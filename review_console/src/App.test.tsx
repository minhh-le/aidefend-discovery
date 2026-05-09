import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const candidates = [
  {
    candidate_key: "content:a",
    candidate_id: "cand-a",
    title: "AGiXT Path Traversal in safe_join()",
    source_type: "GHSA",
    source_id: "GHSA-5gfj-64gh-mgmw",
    severity: "high",
    ecosystem: "pip",
    coverage_score: 25,
    security_score: 95,
    recommended_action: "Promote",
    quality_status: "review_ready",
    quality_label: "Review Ready",
    quality_reason: "Advisory source, identifiers, evidence URL, and attack narrative are present.",
    review_status: "unreviewed",
    review_decision_label: "",
    identifiers: { cves: ["CVE-2026-39981"], ghsas: ["ghsa-5gfj-64gh-mgmw"], cwes: ["CWE-22"] },
    reason_chips: ["low coverage", "reviewed GHSA", "high severity"]
  },
  {
    candidate_key: "source:ghsa_api:GHSA-v6ph-xcq9-qxxj",
    candidate_id: "cand-b",
    title: "mcp-from-openapi SSRF via untrusted OpenAPI $ref",
    source_type: "GHSA",
    source_id: "GHSA-v6ph-xcq9-qxxj",
    severity: "high",
    ecosystem: "npm",
    coverage_score: 80,
    security_score: 95,
    recommended_action: "Merge Into Existing",
    quality_status: "review_ready",
    quality_label: "Review Ready",
    quality_reason: "Advisory source, identifiers, evidence URL, and attack narrative are present.",
    review_status: "merge",
    review_decision_label: "Merge Into Existing",
    identifiers: { cves: ["CVE-2026-39885"], ghsas: ["ghsa-v6ph-xcq9-qxxj"], cwes: ["CWE-918"] },
    reason_chips: ["high severity"]
  },
  {
    candidate_key: "source:rss:langchain-mistralai-1.1.4-release",
    candidate_id: "cand-low",
    title: "langchain-mistralai==1.1.4",
    source_type: "RSS",
    source_id: "langchain-mistralai-1.1.4-release",
    severity: "unknown",
    ecosystem: "",
    coverage_score: 42,
    security_score: 45,
    recommended_action: "Needs Evidence",
    quality_status: "low_signal",
    quality_label: "Low Signal",
    quality_reason: "Broad release-note or package-version item without enough vulnerability narrative.",
    review_status: "unreviewed",
    review_decision_label: "",
    identifiers: { cves: [], ghsas: [], cwes: [] },
    reason_chips: ["low signal"]
  }
];

function detailFor(key: string) {
  const candidate = candidates.find((item) => item.candidate_key === key) || candidates[0];
  return {
    ...candidate,
    review: candidate.review_status === "unreviewed" ? null : { review_decision: "merge", reviewer_notes: "Merge evidence." },
    sections: {
      what_happened: "AGiXT safe_join can let an authenticated attacker traverse out of an agent workspace.",
      why_it_matters: "An attacker may be able to read prompts, tool outputs, or configuration files outside the intended workspace.",
      existing_coverage: "Strongest existing coverage is path normalization and filesystem isolation through AID-H-019.007.",
      gap_assessment: "Likely gap: the source is concrete and the nearest AIDEFEND match is weak.",
      what_this_is: "AGiXT safe_join can let an authenticated attacker traverse out of an agent workspace.",
      why_care: "An attacker may be able to read prompts, tool outputs, or configuration files outside the intended workspace.",
      coverage_assessment: "Strongest existing coverage is path normalization and filesystem isolation through AID-H-019.007.",
      security_assessment: "Likely gap: the source is concrete and the nearest AIDEFEND match is weak.",
      evidence: {
        identifiers: candidate.identifiers,
        packages: ["pip:agixt"],
        versions: ["vulnerable:<= 1.9.1"],
        source_urls: ["https://github.com/Josh-XT/AGiXT/security/advisories/GHSA-5gfj-64gh-mgmw"],
        bridge_rationales: ["CWE-22 maps to path traversal and filesystem isolation risk."]
      },
      similar_techniques: [
        {
          id: "AID-H-019.007",
          name: "AID-H-019.007",
          bm25_score: 2,
          lexical_overlap: ["path", "workspace"],
          coverage_note: "Review coverage gap"
        }
      ],
      provenance: {
        candidate_id: candidate.candidate_id,
        candidate_key: candidate.candidate_key,
        source_type: "ghsa_api",
        source_id: candidate.source_id,
        source_url: "https://github.com/Josh-XT/AGiXT/security/advisories/GHSA-5gfj-64gh-mgmw",
        retrieved_at: "2026-05-05T00:00:00Z",
        max_bm25: 2,
        gap_bm25_max: 10,
        coverage_ceiling: 8,
        source_severity: "high",
        raw_score_details: "max_bm25=2; gap_bm25_max=10",
        gap_reason: "max_bm25_below_threshold",
        bridge_rationale: "CWE bridge",
        license_note: "Sample public advisory metadata.",
        raw_candidate: {},
        raw_gap_report: {}
      }
    }
  };
}

let runPayload: any;

beforeEach(() => {
  runPayload = {
    report_path: "tests/fixtures/sample_gap_run.json",
    report_id: "report",
    generated_at: "2026-05-08T00:00:00Z",
    source: "curated_demo",
    candidate_count: 3,
    review_ready_count: 2,
    needs_enrichment_count: 0,
    low_signal_count: 1,
    reviewed_count: 1,
    run_summary: {
      ingested: 3,
      review_ready: 2,
      needs_enrichment: 0,
      low_signal: 1,
      status_counts: {
        raw_source_item: 0,
        normalized_candidate: 0,
        needs_enrichment: 0,
        review_ready: 2,
        low_signal: 1
      }
    },
    quality_guidance: null,
    presets: [
      {
        id: "curated_demo",
        label: "Curated demo",
        short_label: "Run curated demo",
        description: "Loads real advisory-backed sample data.",
        sources: ["sample"],
        network: false
      },
      {
        id: "live_advisory_scan",
        label: "Live advisory scan",
        short_label: "Run live advisory scan",
        description: "Queries GHSA and NVD.",
        sources: ["ghsa", "nvd"],
        network: true
      },
      {
        id: "broad_source_sweep",
        label: "Broad source sweep",
        short_label: "Run broad source sweep",
        description: "Explores broad source breadth.",
        sources: ["ghsa", "nvd", "rss"],
        network: true
      }
    ],
    source_health: {
      rss: { label: "RSS", status: "available", detail: "1 allowlisted feed", requires_key: false },
      nvd: { label: "NVD", status: "anonymous", detail: "Anonymous mode", requires_key: false },
      ghsa: { label: "GHSA", status: "anonymous", detail: "Anonymous mode", requires_key: false },
      ai: { label: "AI summary", status: "unavailable", detail: "Optional", requires_key: true },
      locality: { label: "Local data", status: "local", detail: "Local only", requires_key: false }
    },
    run_lifecycle: {
      status: "idle",
      preset_id: "",
      current_source: "",
      started_at: "",
      completed_at: "",
      report_path: "tests/fixtures/sample_gap_run.json",
      progress: 0,
      logs: [],
      errors: []
    },
    trust_posture: [
      "Candidates are review hypotheses, not approved AIDEFEND truth.",
      "Reviewer decision is separate from backend recommendation.",
      "Data stays local unless a live source or AI summary is explicitly invoked."
    ]
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/run") {
        return new Response(JSON.stringify(runPayload), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url === "/api/runs" && init?.method === "POST") {
        const body = JSON.parse(String(init.body || "{}"));
        runPayload = {
          ...runPayload,
          report_id: "report-running",
          run_lifecycle: {
            status: "running",
            preset_id: body.preset_id || "curated_demo",
            current_source: "starting",
            started_at: "2026-05-08T00:00:00Z",
            completed_at: "",
            report_path: "tests/fixtures/sample_gap_run.json",
            progress: 10,
            logs: ["started"],
            errors: []
          }
        };
        return new Response(
          JSON.stringify({
            run_lifecycle: runPayload.run_lifecycle
          }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.startsWith("/api/candidates?")) {
        const parsed = new URL(url, "http://localhost");
        if (runPayload.run_lifecycle.status === "running") {
          return new Response(JSON.stringify({ candidates: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
        }
        let items = candidates.filter((item) => item.quality_status === "review_ready");
        if (parsed.searchParams.get("tab") === "reviewed") items = candidates.filter((item) => item.review_status !== "unreviewed");
        if (parsed.searchParams.get("tab") === "needs_enrichment") items = [];
        if (parsed.searchParams.get("tab") === "low_signal") items = candidates.filter((item) => item.quality_status === "low_signal");
        if (parsed.searchParams.get("source_type") === "GHSA") items = items.filter((item) => item.source_type === "GHSA");
        if (parsed.searchParams.get("source_type") === "NVD") items = items.filter((item) => item.source_type === "NVD");
        return new Response(JSON.stringify({ candidates: items }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/review") && init?.method === "POST") {
        return new Response(JSON.stringify({ review: JSON.parse(String(init.body)) }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.startsWith("/api/candidates/")) {
        const key = decodeURIComponent(url.replace("/api/candidates/", ""));
        if (runPayload.run_lifecycle.status === "running") {
          return new Response(JSON.stringify({ error: "Candidate not found." }), { status: 404, headers: { "Content-Type": "application/json" } });
        }
        return new Response(JSON.stringify(detailFor(key)), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return new Response(JSON.stringify({ error: "not found" }), { status: 404, headers: { "Content-Type": "application/json" } });
    })
  );
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("App", () => {
  it("renders the queue with candidates", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Coverage intelligence briefing room" })).toBeInTheDocument();
    expect(await screen.findByText("AGiXT Path Traversal in safe_join()")).toBeInTheDocument();
    expect(screen.getByText("mcp-from-openapi SSRF via untrusted OpenAPI $ref")).toBeInTheDocument();
    expect(screen.getAllByText("3 ingested").length).toBeGreaterThan(0);
    expect(screen.queryByText("langchain-mistralai==1.1.4")).not.toBeInTheDocument();
  });

  it("changes tab and filter candidate list", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "AGiXT Path Traversal in safe_join()" });
    await user.click(screen.getByRole("tab", { name: "Reviewed" }));
    await waitFor(() => expect(screen.getAllByText("mcp-from-openapi SSRF via untrusted OpenAPI $ref").length).toBeGreaterThan(0));
    expect(screen.queryByText("AGiXT Path Traversal in safe_join()")).not.toBeInTheDocument();
    const queue = screen.getByLabelText("Candidate queue");
    await user.selectOptions(within(queue).getByLabelText(/Source/i), "GHSA");
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("source_type=GHSA"), expect.anything()));
  });

  it("selecting a candidate updates the brief", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getAllByText("mcp-from-openapi SSRF via untrusted OpenAPI $ref").length).toBeGreaterThan(0));
    await user.click(screen.getAllByText("mcp-from-openapi SSRF via untrusted OpenAPI $ref")[0]);
    expect(await screen.findByRole("heading", { name: "mcp-from-openapi SSRF via untrusted OpenAPI $ref" })).toBeInTheDocument();
  });

  it("saves a reviewer decision", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "AGiXT Path Traversal in safe_join()" });
    await user.click(screen.getByRole("button", { name: "Promote" }));
    await user.type(screen.getByLabelText(/Reviewer notes/i), "Ready to promote.");
    await user.click(screen.getByRole("button", { name: /Save decision/i }));
    expect(await screen.findByText("Decision saved.")).toBeInTheDocument();
  });

  it("keeps provenance hidden by default and reveals it on demand", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "AGiXT Path Traversal in safe_join()" });
    expect(screen.getByText("Raw score details")).not.toBeVisible();
    await user.click(screen.getByText(/Expert score and raw provenance/i));
    expect(screen.getByText("Raw score details")).toBeVisible();
  });

  it("shows reviewed-only and full-run export actions separately", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "AGiXT Path Traversal in safe_join()" });
    const actions = screen.getByLabelText("Exports");
    expect(actions).toBeTruthy();
    expect(within(actions as HTMLElement).getByText("Reviewed Only")).toBeInTheDocument();
    expect(within(actions as HTMLElement).getByRole("link", { name: /Reviewed Markdown/i })).toHaveAttribute(
      "href",
      "/api/export/reviewed-markdown"
    );
    expect(within(actions as HTMLElement).getByRole("link", { name: /Reviewed CSV/i })).toHaveAttribute(
      "href",
      "/api/export/reviewed-csv"
    );
    expect(within(actions as HTMLElement).getByText("Full Run")).toBeInTheDocument();
    expect(within(actions as HTMLElement).getByRole("link", { name: /All CSV/i })).toHaveAttribute("href", "/api/export/csv");
  });

  it("starts the curated demo from mission control", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Coverage intelligence briefing room" });
    await user.click(screen.getByRole("button", { name: /Run curated demo/i }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith("/api/runs", expect.objectContaining({ method: "POST" })));
  });

  it("hides low-signal release noise until explicitly revealed", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "AGiXT Path Traversal in safe_join()" });
    expect(screen.queryByRole("tab", { name: "Low Signal" })).not.toBeInTheDocument();
    expect(screen.queryByText("langchain-mistralai==1.1.4")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Reveal low-signal items/i }));
    await user.click(screen.getByRole("tab", { name: "Low Signal" }));
    await waitFor(() => expect(screen.getAllByText("langchain-mistralai==1.1.4").length).toBeGreaterThan(0));
  });

  it("clears stale selected candidates while a new run starts", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "AGiXT Path Traversal in safe_join()" });
    await user.click(screen.getByRole("button", { name: /Run live advisory scan/i }));
    await waitFor(() => expect(screen.queryByRole("heading", { name: "AGiXT Path Traversal in safe_join()" })).not.toBeInTheDocument());
    expect(screen.queryByText("Candidate not found.")).not.toBeInTheDocument();
  });
});
