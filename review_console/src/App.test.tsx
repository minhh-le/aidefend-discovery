import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const candidates = [
  {
    candidate_key: "content:a",
    candidate_id: "cand-a",
    title: "Critical Model Loader Deserialization",
    source_type: "GHSA",
    source_id: "GHSA-aaaa-bbbb-cccc",
    severity: "high",
    ecosystem: "pypi",
    coverage_score: 25,
    security_score: 95,
    recommended_action: "Promote",
    review_status: "unreviewed",
    review_decision_label: "",
    identifiers: { cves: ["CVE-2026-0001"], ghsas: ["ghsa-aaaa-bbbb-cccc"], cwes: ["CWE-502"] },
    reason_chips: ["low coverage", "reviewed GHSA", "high severity"]
  },
  {
    candidate_key: "source:nvd_api:CVE-2026-0002",
    candidate_id: "cand-b",
    title: "Known Prompt Injection Variant",
    source_type: "NVD",
    source_id: "CVE-2026-0002",
    severity: "high",
    ecosystem: "",
    coverage_score: 80,
    security_score: 95,
    recommended_action: "Merge Into Existing",
    review_status: "merge",
    review_decision_label: "Merge Into Existing",
    identifiers: { cves: ["CVE-2026-0002"], ghsas: [], cwes: ["CWE-79"] },
    reason_chips: ["high severity"]
  }
];

function detailFor(key: string) {
  const candidate = candidates.find((item) => item.candidate_key === key) || candidates[0];
  return {
    ...candidate,
    review: candidate.review_status === "unreviewed" ? null : { review_decision: "merge", reviewer_notes: "Merge evidence." },
    sections: {
      what_this_is: "A reviewed advisory describes deserialization of untrusted model artifacts.",
      why_care: "The source carries high security signal while lexical coverage is low.",
      coverage_assessment: "Low coverage (25/100). Nearest candidates: AID-H-001.",
      security_assessment: "Severity basis: high. Security Score 95/100.",
      evidence: {
        identifiers: candidate.identifiers,
        packages: ["pypi:model-loader"],
        versions: ["vulnerable:< 1.2.3"],
        source_urls: ["https://github.com/advisories/GHSA-aaaa-bbbb-cccc"],
        bridge_rationales: ["CWE-502 maps to model artifact loading risk."]
      },
      similar_techniques: [
        {
          id: "AID-H-001",
          name: "AID-H-001",
          bm25_score: 2,
          lexical_overlap: ["model", "loading"],
          coverage_note: "Review coverage gap"
        }
      ],
      provenance: {
        candidate_id: candidate.candidate_id,
        candidate_key: candidate.candidate_key,
        source_type: "ghsa_api",
        source_id: candidate.source_id,
        source_url: "https://github.com/advisories/GHSA-aaaa-bbbb-cccc",
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

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/run") {
        return new Response(
          JSON.stringify({
            report_path: "reports/gap_run_20260505.json",
            report_id: "report",
            generated_at: "2026-05-05T00:00:00Z",
            source: "sample",
            candidate_count: 2,
            reviewed_count: 1
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      if (url.startsWith("/api/candidates?")) {
        const parsed = new URL(url, "http://localhost");
        let items = candidates;
        if (parsed.searchParams.get("tab") === "reviewed") items = candidates.filter((item) => item.review_status !== "unreviewed");
        if (parsed.searchParams.get("source_type") === "NVD") items = items.filter((item) => item.source_type === "NVD");
        return new Response(JSON.stringify({ candidates: items }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.endsWith("/review") && init?.method === "POST") {
        return new Response(JSON.stringify({ review: JSON.parse(String(init.body)) }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.startsWith("/api/candidates/")) {
        const key = decodeURIComponent(url.replace("/api/candidates/", ""));
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
    expect(await screen.findByText("Critical Model Loader Deserialization")).toBeInTheDocument();
    expect(screen.getByText("Known Prompt Injection Variant")).toBeInTheDocument();
  });

  it("changes tab and filter candidate list", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Critical Model Loader Deserialization" });
    await user.click(screen.getByRole("tab", { name: "Reviewed" }));
    await waitFor(() => expect(screen.getAllByText("Known Prompt Injection Variant").length).toBeGreaterThan(0));
    expect(screen.queryByText("Critical Model Loader Deserialization")).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(/Source/i), "NVD");
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining("source_type=NVD"), expect.anything()));
  });

  it("selecting a candidate updates the brief", async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getAllByText("Known Prompt Injection Variant").length).toBeGreaterThan(0));
    await user.click(screen.getAllByText("Known Prompt Injection Variant")[0]);
    expect(await screen.findByRole("heading", { name: "Known Prompt Injection Variant" })).toBeInTheDocument();
  });

  it("saves a reviewer decision", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Critical Model Loader Deserialization" });
    await user.click(screen.getByRole("button", { name: "Promote" }));
    await user.type(screen.getByLabelText(/Reviewer notes/i), "Ready to promote.");
    await user.click(screen.getByRole("button", { name: /Save decision/i }));
    expect(await screen.findByText("Decision saved.")).toBeInTheDocument();
  });

  it("keeps provenance hidden by default and reveals it on demand", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: "Critical Model Loader Deserialization" });
    expect(screen.queryByText("Raw score details")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Show score explanation/i }));
    expect(await screen.findByText("Raw score details")).toBeInTheDocument();
  });

  it("shows reviewed-only export actions", async () => {
    render(<App />);
    await screen.findByRole("heading", { name: "Critical Model Loader Deserialization" });
    const actions = screen.getByText("Export Markdown").closest("a")?.parentElement;
    expect(actions).toBeTruthy();
    expect(within(actions as HTMLElement).getByText("Export CSV")).toBeInTheDocument();
  });
});
