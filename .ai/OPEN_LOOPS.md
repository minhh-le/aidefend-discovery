# Open Loops

Updated: 2026-05-02 (promotion playbook + Phase 1 exit hardening)

## High Priority

- [ ] **Open the first upstream promotion PR** per [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) to close the hardened Phase 1 exit. Surfaces any `CandidateFinding` schema gap before MCP integration.
- [ ] **Phase 2 taxonomy-anchor diff** — prerequisite for resuming routine upstream promotions (soft rule in playbook); blocks vocabulary drift from MITRE/OWASP/NIST anchors.
- [ ] **Implement GHSA connector** (`GET /advisories` list/detail, cursor, PAT mode) and CVE↔GHSA enrichment joins.
- [ ] Add NVD authenticated mode (`NVD_API_KEY`) and tune retry/backoff policy for sustained runs.
- [ ] Add stricter AI-relevance/product allowlist filtering for vuln-shaped candidate quality.

## Medium Priority

- [ ] Decide public surface for candidate output: labs docs, MCP-only, website, or another channel.
- [ ] Confirm redistribution boundaries for third-party advisory summaries and extracted text.
- [ ] Optional aidefend-mcp extension: namespaced candidate tools.
- [ ] Grow `lab/aidefend_discovery/gold/` from real gap reports to support quality checks (also unlocks BM25 field-weighting work — see ROADMAP "Deferred with reasoning").

## Resolved

- [x] Initialize safe repo-local `.ai` scaffold.
- [x] Phase 2A NVD connector baseline (anonymous mode + sqlite cursor) integrated into discovery pipeline.
- [x] Rename working identity to AIDEFEND Discovery in repo docs.
- [x] Author [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md); harden Phase 1 exit to require merged upstream PR; add ROADMAP "Deferred with reasoning" section with re-open triggers.
- [x] Fix stale `persistent-agent-security-discovery/*` User-Agent strings in `rss_ingest.py` / `nvd_ingest.py`.
