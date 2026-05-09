import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowDownUp,
  BrainCircuit,
  CheckCircle2,
  ClipboardCopy,
  Database,
  Download,
  ExternalLink,
  FileJson,
  FileText,
  Filter,
  GitMerge,
  Info,
  KeyRound,
  Loader2,
  Play,
  RadioTower,
  Search,
  ShieldCheck,
  TerminalSquare,
  XCircle
} from "lucide-react";
import { fetchActionPacket, generateAiSummary, getCandidate, getRunInfo, listCandidates, saveReview, startRun } from "./api";
import type {
  AiConfig,
  AiSummary,
  CandidateDetail,
  CandidateSummary,
  Filters,
  Preset,
  QueueTab,
  ReviewDecision,
  ReviewState,
  RunInfo,
  RunOptions,
  SourceHealthItem
} from "./types";

const tabs: Array<{ id: QueueTab; label: string; prompt: string }> = [
  { id: "review_ready", label: "Review Ready", prompt: "Advisory-backed candidates with a concrete attack narrative." },
  { id: "needs_enrichment", label: "Needs Enrichment", prompt: "Advisory signal exists, but the narrative or evidence is incomplete." },
  { id: "reviewed", label: "Reviewed", prompt: "Captured human decisions." },
  { id: "low_signal", label: "Low Signal", prompt: "Broad source noise, shown only when explicitly revealed." }
];

const decisionLabels: Record<ReviewDecision, string> = {
  promote: "Promote",
  merge: "Merge Into Existing",
  reject: "Reject",
  needs_evidence: "Needs Evidence",
  monitor: "Monitor"
};

const initialFilters: Filters = {
  source_type: "",
  severity: "",
  coverage_min: "",
  coverage_max: "",
  cwe: "",
  ecosystem: "",
  reviewed: ""
};

const initialRunOptions: RunOptions = {
  max_items: 20,
  feed_url: "",
  allow_custom_feed: false,
  fetch_pages: false,
  nvd_keyword: "machine learning"
};

const initialAiConfig: AiConfig = {
  provider: "openrouter",
  base_url: "https://openrouter.ai/api/v1",
  api_key: "",
  model: ""
};

function join(values: string[] | undefined, fallback = "None observed") {
  return values && values.length ? values.join(", ") : fallback;
}

function decisionClass(decision: string) {
  return `status status-${decision.replace("_", "-")}`;
}

function healthTone(item: SourceHealthItem) {
  if (["available", "enabled", "key_configured", "local"].includes(item.status)) return "good";
  if (item.status === "anonymous") return "warn";
  return "muted";
}

function LoadingState({ label = "Loading review run" }: { label?: string }) {
  return (
    <div className="loading-state" role="status">
      <Loader2 className="spin" size={22} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty-state">
      <Info size={22} aria-hidden="true" />
      <h2>{title}</h2>
      <p>{body}</p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-state" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

function Score({ label, value, tone }: { label: string; value: number; tone: "coverage" | "security" }) {
  return (
    <span className={`score score-${tone}`} aria-label={`${label}: ${value} out of 100`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </span>
  );
}

function SourceHealth({ health }: { health: Record<string, SourceHealthItem> }) {
  const items = ["rss", "nvd", "ghsa", "ai", "locality"]
    .map((key) => health[key])
    .filter(Boolean);
  return (
    <div className="source-health" aria-label="Source health">
      {items.map((item) => (
        <div className={`health-row ${healthTone(item)}`} key={item.label}>
          <span className="health-dot" aria-hidden="true" />
          <div>
            <strong>{item.label}</strong>
            <span>{item.detail}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function WorkflowStrip() {
  const stages = ["Signals", "Candidates", "Coverage", "Gap", "Action Packet"];
  return (
    <ol className="workflow-strip" aria-label="Discovery workflow">
      {stages.map((stage, index) => (
        <li key={stage}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <strong>{stage}</strong>
        </li>
      ))}
    </ol>
  );
}

function RunStatusPanel({ run }: { run: RunInfo | null }) {
  const lifecycle = run?.run_lifecycle;
  if (!lifecycle) return null;
  return (
    <section className="run-status-panel" aria-label="Run status">
      <div className="section-title-row">
        <div>
          <p className="eyebrow">Run Lifecycle</p>
          <h2>{lifecycle.status === "running" ? `Processing ${lifecycle.current_source}` : lifecycle.status.replace("_", " ")}</h2>
        </div>
        <span className={`status status-${lifecycle.status.replace("_", "-")}`}>{lifecycle.status.replace("_", " ")}</span>
      </div>
      <div className="progress-rail" aria-label={`Progress ${lifecycle.progress} percent`}>
        <span style={{ width: `${Math.max(0, Math.min(100, lifecycle.progress))}%` }} />
      </div>
      {lifecycle.errors.length > 0 && (
        <div className="run-errors">
          {lifecycle.errors.map((item) => (
            <p key={item}><AlertTriangle size={14} aria-hidden="true" /> {item}</p>
          ))}
        </div>
      )}
      <details className="log-disclosure" open={lifecycle.status === "running" || lifecycle.errors.length > 0}>
        <summary><TerminalSquare size={15} aria-hidden="true" /> Run log</summary>
        <div className="log-lines">
          {(lifecycle.logs.length ? lifecycle.logs : ["No run log yet."]).map((line) => (
            <code key={line}>{line}</code>
          ))}
        </div>
      </details>
    </section>
  );
}

function MissionControl({
  run,
  options,
  setOptions,
  aiConfig,
  setAiConfig,
  onStart,
  starting
}: {
  run: RunInfo | null;
  options: RunOptions;
  setOptions: (options: RunOptions) => void;
  aiConfig: AiConfig;
  setAiConfig: (config: AiConfig) => void;
  onStart: (presetId: string) => void;
  starting: boolean;
}) {
  const [showConfig, setShowConfig] = useState(false);
  const presets = run?.presets || [];
  const curated = presets.find((preset) => preset.id === "curated_demo");
  const live = presets.find((preset) => preset.id === "live_advisory_scan");
  const broad = presets.find((preset) => preset.id === "broad_source_sweep");

  return (
    <header className="mission-control">
      <div className="briefing-head">
        <div>
          <p className="eyebrow">AIDEFEND Discovery</p>
          <h1>Coverage intelligence briefing room</h1>
          <p className="value-line">
            Turn public security noise into reviewable AIDEFEND coverage intelligence: what happened,
            what defense knowledge exists, what may be missing, and what a maintainer should consider next.
          </p>
        </div>
        <div className="briefing-actions" aria-label="First run actions">
          {curated && (
            <button className="primary-button" type="button" onClick={() => onStart(curated.id)} disabled={starting}>
              {starting ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
              Run curated demo
            </button>
          )}
          {live && (
            <button className="primary-button subtle" type="button" onClick={() => onStart(live.id)} disabled={starting}>
              <RadioTower size={16} aria-hidden="true" />
              Run live advisory scan
            </button>
          )}
          {broad && (
            <button className="secondary-button" type="button" onClick={() => onStart(broad.id)} disabled={starting}>
              <Search size={16} aria-hidden="true" />
              Run broad source sweep
            </button>
          )}
          <button className="secondary-button" type="button" onClick={() => setShowConfig(!showConfig)}>
            <KeyRound size={16} aria-hidden="true" />
            Configure optional keys
          </button>
          <a className="secondary-button" href="#review-workbench">
            <Database size={16} aria-hidden="true" />
            Open latest run
          </a>
        </div>
      </div>

      <WorkflowStrip />

      {run?.quality_guidance && (
        <section className="quality-guidance" aria-label="Quality guidance">
          <AlertTriangle size={18} aria-hidden="true" />
          <p>{run.quality_guidance.message}</p>
          {curated && (
            <button className="secondary-button" type="button" onClick={() => onStart(curated.id)} disabled={starting}>
              <Play size={15} aria-hidden="true" />
              Run curated demo
            </button>
          )}
        </section>
      )}

      <div className="mission-grid">
        <section className="mission-panel">
          <div className="section-title-row">
            <div>
              <p className="eyebrow">Source Health</p>
              <h2>Local first, live on request</h2>
            </div>
            <Activity size={18} aria-hidden="true" />
          </div>
          <SourceHealth health={run?.source_health || {}} />
        </section>

        <section className="mission-panel presets-panel">
          <div className="section-title-row">
            <div>
              <p className="eyebrow">Discovery Presets</p>
              <h2>Choose quality boundary</h2>
            </div>
            <Search size={18} aria-hidden="true" />
          </div>
          <div className="preset-grid">
            {presets.map((preset: Preset) => (
              <button
                className="preset-button"
                type="button"
                key={preset.id}
                onClick={() => onStart(preset.id)}
                disabled={starting}
              >
                <strong>{preset.label}</strong>
                <span>{preset.description}</span>
              </button>
            ))}
          </div>
        </section>
      </div>

      {showConfig && (
        <section className="config-panel" aria-label="Advanced configuration">
          <div className="config-grid">
            <label>
              <span>Max candidates per source</span>
              <input
                inputMode="numeric"
                value={String(options.max_items ?? 20)}
                onChange={(event) => setOptions({ ...options, max_items: Number(event.target.value) || 1 })}
              />
            </label>
            <label>
              <span>RSS feed URL</span>
              <input
                value={options.feed_url || ""}
                onChange={(event) => setOptions({ ...options, feed_url: event.target.value })}
                placeholder="Blank uses the first allowlisted feed"
              />
            </label>
            <label>
              <span>NVD keyword</span>
              <input
                value={options.nvd_keyword || ""}
                onChange={(event) => setOptions({ ...options, nvd_keyword: event.target.value })}
                placeholder="machine learning"
              />
            </label>
            <label>
              <span>AI provider</span>
              <input value={aiConfig.provider} onChange={(event) => setAiConfig({ ...aiConfig, provider: event.target.value })} />
            </label>
            <label>
              <span>AI base URL</span>
              <input value={aiConfig.base_url} onChange={(event) => setAiConfig({ ...aiConfig, base_url: event.target.value })} />
            </label>
            <label>
              <span>AI model</span>
              <input value={aiConfig.model} onChange={(event) => setAiConfig({ ...aiConfig, model: event.target.value })} placeholder="Set AI_SUMMARY_MODEL or paste a model here" />
            </label>
            <label className="wide">
              <span>Session-only AI API key</span>
              <input
                type="password"
                value={aiConfig.api_key}
                onChange={(event) => setAiConfig({ ...aiConfig, api_key: event.target.value })}
                placeholder="Not stored by the demo backend"
              />
            </label>
          </div>
          <div className="toggle-row">
            <label>
              <input
                type="checkbox"
                checked={Boolean(options.allow_custom_feed)}
                onChange={(event) => setOptions({ ...options, allow_custom_feed: event.target.checked })}
              />
              <span>Advanced custom-feed escape hatch</span>
            </label>
            <label>
              <input
                type="checkbox"
                checked={Boolean(options.fetch_pages)}
                onChange={(event) => setOptions({ ...options, fetch_pages: event.target.checked })}
              />
              <span>Fetch allowlisted article pages</span>
            </label>
          </div>
        </section>
      )}

      <RunStatusPanel run={run} />
    </header>
  );
}

function QueuePane({
  run,
  tab,
  setTab,
  filters,
  setFilters,
  candidates,
  selectedKey,
  onSelect,
  loading
}: {
  run: RunInfo | null;
  tab: QueueTab;
  setTab: (tab: QueueTab) => void;
  filters: Filters;
  setFilters: (filters: Filters) => void;
  candidates: CandidateSummary[];
  selectedKey: string;
  onSelect: (candidateKey: string) => void;
  loading: boolean;
}) {
  const [showLowSignal, setShowLowSignal] = useState(false);
  const visibleTabs = tabs.filter((item) => item.id !== "low_signal" || showLowSignal || tab === "low_signal");
  const summary = run?.run_summary;
  return (
    <aside className="queue-pane" aria-label="Candidate queue">
      <div className="pane-header">
        <div>
          <p className="eyebrow">Candidate Queue</p>
          <h2>{run?.review_ready_count ?? 0} review-ready</h2>
        </div>
        <div className="run-count" aria-label="Reviewed candidates">
          <strong>{run?.reviewed_count ?? 0}</strong>
          <span>reviewed</span>
        </div>
      </div>

      <div className="quality-counts" aria-label="Run quality summary">
        <span>{summary?.ingested ?? run?.candidate_count ?? 0} ingested</span>
        <span>{summary?.review_ready ?? 0} review-ready</span>
        <span>{summary?.needs_enrichment ?? 0} needs enrichment</span>
        <span>{summary?.low_signal ?? 0} low signal</span>
      </div>

      <div className="tabs" role="tablist" aria-label="Queue tabs">
        {visibleTabs.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? "tab active" : "tab"}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {!showLowSignal && (
        <button className="reveal-button" type="button" onClick={() => setShowLowSignal(true)}>
          Reveal low-signal items
        </button>
      )}
      <p className="queue-prompt">{tabs.find((item) => item.id === tab)?.prompt}</p>

      <div className="filters" aria-label="Candidate filters">
        <label>
          <span><Filter size={13} aria-hidden="true" /> Source</span>
          <select value={filters.source_type} onChange={(event) => setFilters({ ...filters, source_type: event.target.value })}>
            <option value="">All sources</option>
            <option value="GHSA">GHSA</option>
            <option value="NVD">NVD</option>
            <option value="RSS">RSS</option>
          </select>
        </label>
        <label>
          <span>Severity</span>
          <select value={filters.severity} onChange={(event) => setFilters({ ...filters, severity: event.target.value })}>
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="unknown">Unknown</option>
          </select>
        </label>
        <div className="range-row">
          <label>
            <span>Coverage min</span>
            <input inputMode="numeric" value={filters.coverage_min} onChange={(event) => setFilters({ ...filters, coverage_min: event.target.value })} />
          </label>
          <label>
            <span>Coverage max</span>
            <input inputMode="numeric" value={filters.coverage_max} onChange={(event) => setFilters({ ...filters, coverage_max: event.target.value })} />
          </label>
        </div>
        <div className="range-row">
          <label>
            <span>CWE</span>
            <input placeholder="CWE-502" value={filters.cwe} onChange={(event) => setFilters({ ...filters, cwe: event.target.value })} />
          </label>
          <label>
            <span>Ecosystem</span>
            <input placeholder="pypi" value={filters.ecosystem} onChange={(event) => setFilters({ ...filters, ecosystem: event.target.value })} />
          </label>
        </div>
      </div>

      <div className="candidate-list" aria-label="Candidates">
        {loading ? (
          <LoadingState label="Loading candidates" />
        ) : candidates.length === 0 ? (
          <EmptyState title="No candidates match" body="Adjust filters or choose another queue tab." />
        ) : (
          candidates.map((candidate) => (
            <button
              key={candidate.candidate_key}
              className={selectedKey === candidate.candidate_key ? "candidate-row selected" : "candidate-row"}
              onClick={() => onSelect(candidate.candidate_key)}
            >
              <span className="row-topline">
                <strong>{candidate.title}</strong>
                <span className="source-pill">{candidate.source_type}</span>
              </span>
              <span className="row-scores">
                <Score label="Coverage" value={candidate.coverage_score} tone="coverage" />
                <Score label="Security" value={candidate.security_score} tone="security" />
              </span>
              <span className="row-meta">
                <span>{candidate.quality_label}</span>
                <span>{candidate.recommended_action}</span>
                <span className={decisionClass(candidate.review_status)}>
                  {candidate.review_decision_label || "unreviewed"}
                </span>
              </span>
              <span className="quality-reason">{candidate.quality_reason}</span>
              <span className="identifier-line">
                {join([...candidate.identifiers.cves, ...candidate.identifiers.ghsas, ...candidate.identifiers.cwes], "No identifiers")}
              </span>
              <span className="chip-row">
                {candidate.reason_chips.map((chip) => (
                  <span className="reason-chip" key={chip}>{chip}</span>
                ))}
              </span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}

function BriefPane({
  detail,
  loading,
  aiConfig
}: {
  detail: CandidateDetail | null;
  loading: boolean;
  aiConfig: AiConfig;
}) {
  const [aiResult, setAiResult] = useState<AiSummary | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    setAiResult(null);
    setAiLoading(false);
  }, [detail?.candidate_key]);

  async function requestAiSummary() {
    if (!detail) return;
    setAiLoading(true);
    try {
      setAiResult(await generateAiSummary(detail.candidate_key, aiConfig));
    } finally {
      setAiLoading(false);
    }
  }

  if (loading) {
    return <main className="brief-pane"><LoadingState label="Loading candidate brief" /></main>;
  }
  if (!detail) {
    return <main className="brief-pane"><EmptyState title="Select a candidate" body="Review what happened, what AIDEFEND covers, and what evidence supports the recommendation." /></main>;
  }

  return (
    <main className="brief-pane" id="candidate-brief">
      <div className="brief-header">
        <div>
          <p className="eyebrow">{detail.source_id}</p>
          <h2>{detail.title}</h2>
        </div>
        <div className="header-score-strip">
          <Score label="Coverage" value={detail.coverage_score} tone="coverage" />
          <Score label="Security" value={detail.security_score} tone="security" />
        </div>
      </div>

      <div className="action-strip" aria-label="Recommendation summary">
        <span><Info size={16} aria-hidden="true" /> Quality: {detail.quality_label}</span>
        <span><ShieldCheck size={16} aria-hidden="true" /> Backend: {detail.recommended_action}</span>
        <span className={decisionClass(detail.review_status)}>
          Reviewer: {detail.review_decision_label || "unreviewed"}
        </span>
      </div>

      <section className="brief-section">
        <h3>What happened?</h3>
        <p>{detail.sections.what_happened}</p>
      </section>

      <section className="brief-section emphasis-section">
        <h3>Why does it matter?</h3>
        <p>{detail.sections.why_it_matters}</p>
      </section>

      <div className="split-sections">
        <section className="brief-section">
          <h3>What does AIDEFEND already cover?</h3>
          <p>{detail.sections.existing_coverage}</p>
        </section>
        <section className="brief-section">
          <h3>Is this likely a gap?</h3>
          <p>{detail.sections.gap_assessment}</p>
        </section>
      </div>

      <section className="brief-section ai-section">
        <div className="section-title-row">
          <div>
            <h3>Optional AI briefing</h3>
            <p>On demand only. Sends compact candidate context, not full extracted bodies.</p>
          </div>
          <button className="secondary-button" type="button" onClick={requestAiSummary} disabled={aiLoading}>
            {aiLoading ? <Loader2 className="spin" size={15} aria-hidden="true" /> : <BrainCircuit size={15} aria-hidden="true" />}
            Generate
          </button>
        </div>
        {aiResult && (
          <div className={`ai-output ${aiResult.fallback_used ? "fallback" : "ok"}`}>
            <strong>{aiResult.fallback_used ? "AI unavailable, deterministic summary shown" : "AI summary"}</strong>
            {aiResult.error && <p>{aiResult.error}</p>}
            <pre>{aiResult.summary}</pre>
          </div>
        )}
      </section>

      <section className="brief-section">
        <div className="section-title-row">
          <h3>Nearest AIDEFEND comparison</h3>
          <ArrowDownUp size={16} aria-hidden="true" />
        </div>
        {detail.sections.similar_techniques.length === 0 ? (
          <p>No nearest technique was reported. Treat this as a stronger gap signal until evidence says otherwise.</p>
        ) : (
          <div className="comparison-grid">
            <div className="comparison-panel candidate-side">
              <span className="panel-label">Candidate</span>
              <strong>{detail.title}</strong>
              <p>{detail.sections.existing_coverage}</p>
            </div>
            <div className="comparison-panel">
              <span className="panel-label">Nearest technique</span>
              <strong>{detail.sections.similar_techniques[0].id}</strong>
              <p>{detail.sections.similar_techniques[0].coverage_note}</p>
              <p className="overlap-text">Lexical overlap: {join(detail.sections.similar_techniques[0].lexical_overlap)}</p>
            </div>
          </div>
        )}
        <div className="technique-list">
          {detail.sections.similar_techniques.map((technique) => (
            <div className="technique-row" key={technique.id}>
              <strong>{technique.id}</strong>
              <span>BM25 {technique.bm25_score ?? "n/a"}</span>
              <span>{join(technique.lexical_overlap, "No lexical overlap")}</span>
            </div>
          ))}
        </div>
      </section>

      <details className="brief-disclosure" open>
        <summary><Info size={16} aria-hidden="true" /> Evidence</summary>
        <dl className="evidence-grid">
          <div><dt>CVE</dt><dd>{join(detail.sections.evidence.identifiers.cves)}</dd></div>
          <div><dt>GHSA</dt><dd>{join(detail.sections.evidence.identifiers.ghsas)}</dd></div>
          <div><dt>CWE</dt><dd>{join(detail.sections.evidence.identifiers.cwes)}</dd></div>
          <div><dt>Packages</dt><dd>{join(detail.sections.evidence.packages)}</dd></div>
          <div><dt>Versions</dt><dd>{join(detail.sections.evidence.versions)}</dd></div>
          <div><dt>Bridge</dt><dd>{join(detail.sections.evidence.bridge_rationales)}</dd></div>
          <div className="wide"><dt>Source URLs</dt><dd>{join(detail.sections.evidence.source_urls)}</dd></div>
        </dl>
      </details>

      <details className="brief-disclosure">
        <summary><FileJson size={16} aria-hidden="true" /> Expert score and raw provenance</summary>
        <dl className="provenance-grid">
          <div><dt>max BM25</dt><dd>{detail.sections.provenance.max_bm25 ?? "missing"}</dd></div>
          <div><dt>gap_bm25_max</dt><dd>{detail.sections.provenance.gap_bm25_max ?? "missing"}</dd></div>
          <div><dt>Source severity</dt><dd>{detail.sections.provenance.source_severity}</dd></div>
          <div><dt>Candidate ID</dt><dd>{detail.sections.provenance.candidate_id}</dd></div>
          <div><dt>Candidate key</dt><dd>{detail.sections.provenance.candidate_key}</dd></div>
          <div><dt>Retrieved</dt><dd>{detail.sections.provenance.retrieved_at}</dd></div>
          <div className="wide"><dt>Gap reason</dt><dd>{detail.sections.provenance.gap_reason}</dd></div>
          <div className="wide"><dt>Raw score details</dt><dd>{detail.sections.provenance.raw_score_details}</dd></div>
          <div className="wide"><dt>License note</dt><dd>{detail.sections.provenance.license_note}</dd></div>
          <div className="wide"><dt>Source URL</dt><dd>{detail.sections.provenance.source_url || "None observed"}</dd></div>
        </dl>
      </details>
    </main>
  );
}

function DecisionPanel({ detail, onSaved }: { detail: CandidateDetail | null; onSaved: () => void }) {
  const [form, setForm] = useState<ReviewState>({ review_decision: "monitor" });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [packetMessage, setPacketMessage] = useState("");

  useEffect(() => {
    setMessage("");
    setPacketMessage("");
    setForm({
      review_decision: detail?.review?.review_decision || "monitor",
      reviewer_notes: detail?.review?.reviewer_notes || "",
      assigned_owner: detail?.review?.assigned_owner || "",
      confidence: detail?.review?.confidence || "",
      merge_target: detail?.review?.merge_target || "",
      promotion_target: detail?.review?.promotion_target || "",
      proposed_tactic: detail?.review?.proposed_tactic || "",
      proposed_title: detail?.review?.proposed_title || "",
      supporting_evidence: detail?.review?.supporting_evidence || "",
      nearest_checked: detail?.review?.nearest_checked || "",
      evidence_to_add: detail?.review?.evidence_to_add || "",
      not_new_reason: detail?.review?.not_new_reason || ""
    });
  }, [detail?.candidate_key]);

  async function submit() {
    if (!detail || !form.review_decision) return;
    setSaving(true);
    setMessage("");
    try {
      await saveReview(detail.candidate_key, form);
      setMessage("Decision saved.");
      onSaved();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Decision could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function copyPacket() {
    if (!detail) return;
    setPacketMessage("");
    try {
      const packet = await fetchActionPacket(detail.candidate_key);
      await navigator.clipboard.writeText(packet);
      setPacketMessage("Action packet copied.");
    } catch (error) {
      setPacketMessage(error instanceof Error ? error.message : "Action packet could not be copied.");
    }
  }

  if (!detail) {
    return (
      <aside className="decision-pane" aria-label="Decision panel">
        <EmptyState title="No candidate selected" body="Select a candidate to capture a reviewer decision." />
      </aside>
    );
  }

  const needsPromoteFields = form.review_decision === "promote";
  const needsMergeFields = form.review_decision === "merge";

  return (
    <aside className="decision-pane" aria-label="Decision panel">
      <div className="pane-header compact">
        <div>
          <p className="eyebrow">Reviewer Decision</p>
          <h2>Human call, separate from backend</h2>
        </div>
      </div>

      <div className="decision-buttons" aria-label="Decision actions">
        {(Object.keys(decisionLabels) as ReviewDecision[]).map((decision) => (
          <button
            key={decision}
            className={form.review_decision === decision ? "decision-button active" : "decision-button"}
            onClick={() => setForm({ ...form, review_decision: decision })}
            type="button"
          >
            {decision === "promote" && <CheckCircle2 size={16} aria-hidden="true" />}
            {decision === "merge" && <GitMerge size={16} aria-hidden="true" />}
            {decision === "reject" && <XCircle size={16} aria-hidden="true" />}
            {decision !== "promote" && decision !== "merge" && decision !== "reject" && <Info size={16} aria-hidden="true" />}
            {decisionLabels[decision]}
          </button>
        ))}
      </div>

      <div className="form-stack">
        <label>
          <span>Reviewer notes</span>
          <textarea value={form.reviewer_notes || ""} onChange={(event) => setForm({ ...form, reviewer_notes: event.target.value })} rows={5} />
        </label>
        <label>
          <span>Assigned owner</span>
          <input value={form.assigned_owner || ""} onChange={(event) => setForm({ ...form, assigned_owner: event.target.value })} />
        </label>
        <label>
          <span>Confidence</span>
          <select value={form.confidence || ""} onChange={(event) => setForm({ ...form, confidence: event.target.value })}>
            <option value="">Unspecified</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label>
          <span>Selected existing AIDEFEND technique</span>
          <input value={form.merge_target || ""} onChange={(event) => setForm({ ...form, merge_target: event.target.value })} placeholder="AID-H-031" />
        </label>
        <label>
          <span>Promotion target</span>
          <input value={form.promotion_target || ""} onChange={(event) => setForm({ ...form, promotion_target: event.target.value })} placeholder="vendor/aidefense-framework/tactics/harden.js" />
        </label>

        <div className={needsPromoteFields ? "guidance active" : "guidance"}>
          <strong>Promote checklist</strong>
          <label>
            <span>Proposed tactic</span>
            <input value={form.proposed_tactic || ""} onChange={(event) => setForm({ ...form, proposed_tactic: event.target.value })} />
          </label>
          <label>
            <span>Proposed technique or subtechnique title</span>
            <input value={form.proposed_title || ""} onChange={(event) => setForm({ ...form, proposed_title: event.target.value })} />
          </label>
          <label>
            <span>Supporting evidence</span>
            <textarea value={form.supporting_evidence || ""} onChange={(event) => setForm({ ...form, supporting_evidence: event.target.value })} rows={3} />
          </label>
          <label>
            <span>Nearest techniques checked</span>
            <input value={form.nearest_checked || ""} onChange={(event) => setForm({ ...form, nearest_checked: event.target.value })} />
          </label>
        </div>

        <div className={needsMergeFields ? "guidance active" : "guidance"}>
          <strong>Merge checklist</strong>
          <label>
            <span>Evidence to add</span>
            <textarea value={form.evidence_to_add || ""} onChange={(event) => setForm({ ...form, evidence_to_add: event.target.value })} rows={3} />
          </label>
          <label>
            <span>Why this should not be a new technique</span>
            <textarea value={form.not_new_reason || ""} onChange={(event) => setForm({ ...form, not_new_reason: event.target.value })} rows={3} />
          </label>
        </div>
      </div>

      <div className="export-menu" aria-label="Exports">
        <p className="trust-note">
          Candidate-only output. Backend recommendations and reviewer decisions are not approved AIDEFEND truth.
        </p>
        <div className="export-group">
          <span className="export-group-label">Reviewed Only</span>
          <a className="secondary-button" href="/api/export/reviewed-markdown">
            <FileText size={15} aria-hidden="true" /> Reviewed Markdown
          </a>
          <a className="secondary-button" href="/api/export/reviewed-csv">
            <Download size={15} aria-hidden="true" /> Reviewed CSV
          </a>
        </div>
        <div className="export-group">
          <span className="export-group-label">Full Run</span>
          <a className="secondary-button" href="/api/export/markdown">
            <FileText size={15} aria-hidden="true" /> All Markdown
          </a>
          <a className="secondary-button" href="/api/export/csv">
            <Download size={15} aria-hidden="true" /> All CSV
          </a>
          <a className="secondary-button" href="/api/export/json">
            <FileJson size={15} aria-hidden="true" /> All JSON
          </a>
        </div>
        <div className="export-group">
          <span className="export-group-label">Selected Candidate</span>
          <button className="secondary-button" type="button" onClick={copyPacket}>
            <ClipboardCopy size={15} aria-hidden="true" /> Copy Action Packet
          </button>
          <a className="secondary-button" href={`/api/export/action-packet?candidate_key=${encodeURIComponent(detail.candidate_key)}`}>
            <FileText size={15} aria-hidden="true" /> Action Packet
          </a>
        </div>
      </div>

      <div className="decision-footer">
        <a className="link-button" href={detail.sections.provenance.source_url || "#"} target="_blank" rel="noreferrer">
          <ExternalLink size={15} aria-hidden="true" /> Source advisory
        </a>
        <button className="primary-button" type="button" onClick={submit} disabled={saving}>
          {saving ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <ShieldCheck size={16} aria-hidden="true" />}
          Save decision
        </button>
        {message && <p className={message === "Decision saved." ? "save-message success" : "save-message error"}>{message}</p>}
        {packetMessage && <p className={packetMessage === "Action packet copied." ? "save-message success" : "save-message error"}>{packetMessage}</p>}
      </div>
    </aside>
  );
}

export function App() {
  const [run, setRun] = useState<RunInfo | null>(null);
  const [tab, setTab] = useState<QueueTab>("review_ready");
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [options, setOptions] = useState<RunOptions>(initialRunOptions);
  const [aiConfig, setAiConfig] = useState<AiConfig>(initialAiConfig);
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [loadingRun, setLoadingRun] = useState(true);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const selectedExists = useMemo(() => candidates.some((candidate) => candidate.candidate_key === selectedKey), [candidates, selectedKey]);
  const runKey = `${run?.report_id || ""}:${run?.candidate_count || 0}:${run?.reviewed_count || 0}:${run?.run_lifecycle.status || ""}:${run?.run_lifecycle.report_path || ""}`;

  async function refreshRun() {
    const info = await getRunInfo();
    setRun(info);
    return info;
  }

  async function refreshQueue(nextSelectedKey = selectedKey) {
    setLoadingQueue(true);
    try {
      const items = await listCandidates(tab, filters);
      setCandidates(items);
      const key = nextSelectedKey && items.some((item) => item.candidate_key === nextSelectedKey) ? nextSelectedKey : items[0]?.candidate_key || "";
      setSelectedKey(key);
      return key;
    } finally {
      setLoadingQueue(false);
    }
  }

  async function handleStart(presetId: string) {
    setStarting(true);
    setError("");
    setCandidates([]);
    setSelectedKey("");
    setDetail(null);
    setTab("review_ready");
    try {
      await startRun(presetId, options);
      await refreshRun();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run could not start.");
    } finally {
      setStarting(false);
    }
  }

  useEffect(() => {
    let active = true;
    setLoadingRun(true);
    setError("");
    getRunInfo()
      .then((info) => {
        if (active) setRun(info);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Review console could not load.");
      })
      .finally(() => {
        if (active) setLoadingRun(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (run?.run_lifecycle.status !== "running") return;
    const timer = window.setInterval(() => {
      refreshRun().catch((err) => setError(err instanceof Error ? err.message : "Run status could not refresh."));
    }, 1200);
    return () => window.clearInterval(timer);
  }, [run?.run_lifecycle.status]);

  useEffect(() => {
    if (run?.run_lifecycle.status === "running") {
      setCandidates([]);
      setSelectedKey("");
      setDetail(null);
      setLoadingQueue(false);
      return;
    }
    let active = true;
    setLoadingQueue(true);
    setError("");
    listCandidates(tab, filters)
      .then((items) => {
        if (!active) return;
        setCandidates(items);
        setSelectedKey((current) => (items.some((item) => item.candidate_key === current) ? current : items[0]?.candidate_key || ""));
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Candidates could not load.");
      })
      .finally(() => {
        if (active) setLoadingQueue(false);
      });
    return () => {
      active = false;
    };
  }, [tab, filters, runKey, run?.run_lifecycle.status]);

  useEffect(() => {
    if (!selectedKey || !selectedExists) {
      setDetail(null);
      setLoadingDetail(false);
      return;
    }
    let active = true;
    setLoadingDetail(true);
    getCandidate(selectedKey)
      .then((candidate) => {
        if (active) setDetail(candidate);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Candidate could not load.");
      })
      .finally(() => {
        if (active) setLoadingDetail(false);
      });
    return () => {
      active = false;
    };
  }, [selectedKey, selectedExists, runKey]);

  async function handleSaved() {
    await refreshRun();
    const key = await refreshQueue(selectedKey);
    if (key) {
      setDetail(await getCandidate(key));
    }
  }

  if (loadingRun) return <LoadingState />;

  return (
    <div className="app-shell">
      <a href="#candidate-brief" className="skip-link">Skip to candidate brief</a>
      {error && <ErrorState message={error} />}
      <MissionControl
        run={run}
        options={options}
        setOptions={setOptions}
        aiConfig={aiConfig}
        setAiConfig={setAiConfig}
        onStart={handleStart}
        starting={starting || run?.run_lifecycle.status === "running"}
      />
      <div className="run-summary-bar" id="review-workbench">
        <span><Database size={15} aria-hidden="true" /> {run?.report_path || "No report loaded"}</span>
        <span>{run?.run_summary?.ingested ?? run?.candidate_count ?? 0} ingested</span>
        <span>{run?.run_summary?.review_ready ?? 0} review-ready</span>
        <span>{run?.run_summary?.needs_enrichment ?? 0} needs enrichment</span>
        <span>{run?.run_summary?.low_signal ?? 0} low signal</span>
        <span>{run?.source || "curated_demo"} source</span>
      </div>
      <div className="workbench">
        <QueuePane
          run={run}
          tab={tab}
          setTab={setTab}
          filters={filters}
          setFilters={setFilters}
          candidates={candidates}
          selectedKey={selectedKey}
          onSelect={setSelectedKey}
          loading={loadingQueue}
        />
        <BriefPane detail={detail} loading={loadingDetail} aiConfig={aiConfig} />
        <DecisionPanel detail={detail} onSaved={handleSaved} />
      </div>
    </div>
  );
}
