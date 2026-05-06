import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowDownUp,
  CheckCircle2,
  ClipboardCopy,
  Download,
  ExternalLink,
  FileText,
  Filter,
  GitMerge,
  Info,
  Loader2,
  Search,
  ShieldCheck,
  XCircle
} from "lucide-react";
import { getCandidate, getRunInfo, listCandidates, saveReview } from "./api";
import type { CandidateDetail, CandidateSummary, Filters, QueueTab, ReviewDecision, ReviewState, RunInfo } from "./types";

const tabs: Array<{ id: QueueTab; label: string; prompt: string }> = [
  { id: "lowest", label: "Lowest Coverage", prompt: "What might AIDEFEND be missing?" },
  { id: "highest", label: "Highest Severity", prompt: "What should practitioners care about?" },
  { id: "needs_evidence", label: "Needs Evidence", prompt: "What needs corroboration?" },
  { id: "monitor", label: "Monitor", prompt: "What should stay on the radar?" },
  { id: "reviewed", label: "Reviewed", prompt: "What has a captured decision?" }
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

function join(values: string[] | undefined, fallback = "None observed") {
  return values && values.length ? values.join(", ") : fallback;
}

function decisionClass(decision: string) {
  return `status status-${decision.replace("_", "-")}`;
}

function Score({ label, value, tone }: { label: string; value: number; tone: "coverage" | "security" }) {
  return (
    <span className={`score score-${tone}`} aria-label={`${label}: ${value} out of 100`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </span>
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

function LoadingState() {
  return (
    <div className="loading-state" role="status">
      <Loader2 className="spin" size={22} aria-hidden="true" />
      <span>Loading review run...</span>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="error-state" role="alert">
      <AlertTriangle size={22} aria-hidden="true" />
      <span>{message}</span>
    </div>
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
  return (
    <aside className="queue-pane" aria-label="Review queue">
      <div className="pane-header">
        <div>
          <p className="eyebrow">Review Queue</p>
          <h1>AIDEFEND Discovery</h1>
        </div>
        <div className="run-count" aria-label="Reviewed candidates">
          <strong>{run?.reviewed_count ?? 0}</strong>
          <span>reviewed</span>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Queue tabs">
        {tabs.map((item) => (
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
        <label>
          <span>Review state</span>
          <select value={filters.reviewed} onChange={(event) => setFilters({ ...filters, reviewed: event.target.value })}>
            <option value="">All states</option>
            <option value="unreviewed">Unreviewed</option>
            <option value="reviewed">Reviewed</option>
          </select>
        </label>
      </div>

      <div className="candidate-list" aria-label="Candidates">
        {loading ? (
          <LoadingState />
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
                <span>{candidate.recommended_action}</span>
                <span className={decisionClass(candidate.review_status)}>
                  {candidate.review_decision_label || "unreviewed"}
                </span>
              </span>
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

function BriefPane({ detail, loading }: { detail: CandidateDetail | null; loading: boolean }) {
  const [showProvenance, setShowProvenance] = useState(false);

  useEffect(() => {
    setShowProvenance(false);
  }, [detail?.candidate_key]);

  if (loading) {
    return <main className="brief-pane"><LoadingState /></main>;
  }
  if (!detail) {
    return <main className="brief-pane"><EmptyState title="Select a candidate" body="Choose an item from the queue to inspect the brief and comparison." /></main>;
  }

  return (
    <main className="brief-pane" id="main-content">
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
        <span><ShieldCheck size={16} aria-hidden="true" /> Backend: {detail.recommended_action}</span>
        <span className={decisionClass(detail.review_status)}>
          Reviewer: {detail.review_decision_label || "unreviewed"}
        </span>
      </div>

      <section className="brief-section">
        <h3>What This Is</h3>
        <p>{detail.sections.what_this_is}</p>
      </section>

      <section className="brief-section care-section">
        <h3>Why AIDEFEND Should Care</h3>
        <p>{detail.sections.why_care}</p>
      </section>

      <div className="split-sections">
        <section className="brief-section">
          <h3>Coverage Assessment</h3>
          <p>{detail.sections.coverage_assessment}</p>
        </section>
        <section className="brief-section">
          <h3>Security Assessment</h3>
          <p>{detail.sections.security_assessment}</p>
        </section>
      </div>

      <section className="brief-section">
        <h3>Evidence</h3>
        <dl className="evidence-grid">
          <div><dt>CVE</dt><dd>{join(detail.sections.evidence.identifiers.cves)}</dd></div>
          <div><dt>GHSA</dt><dd>{join(detail.sections.evidence.identifiers.ghsas)}</dd></div>
          <div><dt>CWE</dt><dd>{join(detail.sections.evidence.identifiers.cwes)}</dd></div>
          <div><dt>Packages</dt><dd>{join(detail.sections.evidence.packages)}</dd></div>
          <div><dt>Versions</dt><dd>{join(detail.sections.evidence.versions)}</dd></div>
          <div><dt>Bridge</dt><dd>{join(detail.sections.evidence.bridge_rationales)}</dd></div>
        </dl>
      </section>

      <section className="brief-section">
        <div className="section-title-row">
          <h3>Similar AIDEFEND Techniques</h3>
          <ArrowDownUp size={16} aria-hidden="true" />
        </div>
        {detail.sections.similar_techniques.length === 0 ? (
          <p>No nearest technique was reported. Treat this as a stronger gap signal until evidence says otherwise.</p>
        ) : (
          <div className="comparison-grid">
            <div className="comparison-panel candidate-side">
              <span className="panel-label">Candidate</span>
              <strong>{detail.title}</strong>
              <p>{detail.sections.coverage_assessment}</p>
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

      <section className="brief-section provenance-section">
        <button className="secondary-button" onClick={() => setShowProvenance(!showProvenance)} aria-expanded={showProvenance}>
          <Info size={16} aria-hidden="true" />
          {showProvenance ? "Hide score explanation" : "Show score explanation"}
        </button>
        {showProvenance && (
          <dl className="provenance-grid">
            <div><dt>max BM25</dt><dd>{detail.sections.provenance.max_bm25 ?? "missing"}</dd></div>
            <div><dt>gap_bm25_max</dt><dd>{detail.sections.provenance.gap_bm25_max ?? "missing"}</dd></div>
            <div><dt>Source severity</dt><dd>{detail.sections.provenance.source_severity}</dd></div>
            <div><dt>Candidate ID</dt><dd>{detail.sections.provenance.candidate_id}</dd></div>
            <div><dt>Source type</dt><dd>{detail.sections.provenance.source_type}</dd></div>
            <div><dt>Retrieved</dt><dd>{detail.sections.provenance.retrieved_at}</dd></div>
            <div className="wide"><dt>Gap reason</dt><dd>{detail.sections.provenance.gap_reason}</dd></div>
            <div className="wide"><dt>Raw score details</dt><dd>{detail.sections.provenance.raw_score_details}</dd></div>
            <div className="wide"><dt>Source URL</dt><dd>{detail.sections.provenance.source_url || "None observed"}</dd></div>
          </dl>
        )}
      </section>
    </main>
  );
}

function DecisionPanel({ detail, onSaved }: { detail: CandidateDetail | null; onSaved: () => void }) {
  const [form, setForm] = useState<ReviewState>({ review_decision: "monitor" });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setMessage("");
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
          <p className="eyebrow">Decision Panel</p>
          <h2>Capture review</h2>
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
          <input value={form.promotion_target || ""} onChange={(event) => setForm({ ...form, promotion_target: event.target.value })} placeholder="tactics/harden.js" />
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
            <span>Nearest existing techniques checked</span>
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

      <div className="decision-footer">
        <a className="link-button" href={detail.sections.provenance.source_url || "#"} target="_blank" rel="noreferrer">
          <ExternalLink size={15} aria-hidden="true" /> Source advisory
        </a>
        <button className="secondary-button" type="button" disabled>
          <ClipboardCopy size={15} aria-hidden="true" /> Copy promotion summary
        </button>
        <button className="secondary-button" type="button" disabled>Create promotion draft</button>
        <button className="primary-button" type="button" onClick={submit} disabled={saving}>
          {saving ? <Loader2 className="spin" size={16} aria-hidden="true" /> : <ShieldCheck size={16} aria-hidden="true" />}
          Save decision
        </button>
        {message && <p className={message === "Decision saved." ? "save-message success" : "save-message error"}>{message}</p>}
      </div>
    </aside>
  );
}

export function App() {
  const [run, setRun] = useState<RunInfo | null>(null);
  const [tab, setTab] = useState<QueueTab>("lowest");
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [loadingRun, setLoadingRun] = useState(true);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState("");
  const selectedExists = useMemo(() => candidates.some((candidate) => candidate.candidate_key === selectedKey), [candidates, selectedKey]);

  async function refreshRun() {
    setRun(await getRunInfo());
  }

  async function refreshQueue(nextSelectedKey = selectedKey) {
    setLoadingQueue(true);
    try {
      const items = await listCandidates(tab, filters);
      setCandidates(items);
      const key = nextSelectedKey && items.some((item) => item.candidate_key === nextSelectedKey) ? nextSelectedKey : items[0]?.candidate_key || "";
      setSelectedKey(key);
    } finally {
      setLoadingQueue(false);
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
  }, [tab, filters]);

  useEffect(() => {
    if (!selectedKey || !selectedExists) {
      setDetail(null);
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
  }, [selectedKey, selectedExists]);

  async function handleSaved() {
    await refreshRun();
    await refreshQueue(selectedKey);
    if (selectedKey) {
      setDetail(await getCandidate(selectedKey));
    }
  }

  if (loadingRun) return <LoadingState />;

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">Skip to candidate brief</a>
      {error && <ErrorState message={error} />}
      <header className="topbar">
        <div>
          <p className="eyebrow">Public Demo Console</p>
          <strong>{run?.report_path || "No report loaded"}</strong>
        </div>
        <div className="topbar-actions">
          <span>{run?.candidate_count ?? 0} candidates</span>
          <a className="secondary-button" href="/api/export/markdown">
            <FileText size={16} aria-hidden="true" /> Export Markdown
          </a>
          <a className="secondary-button" href="/api/export/csv">
            <Download size={16} aria-hidden="true" /> Export CSV
          </a>
        </div>
      </header>
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
        <BriefPane detail={detail} loading={loadingDetail} />
        <DecisionPanel detail={detail} onSaved={handleSaved} />
      </div>
    </div>
  );
}
