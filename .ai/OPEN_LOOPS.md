# Open Loops

Updated: 2026-05-02

## High Priority

- [ ] **Implement GHSA connector** (`GET /advisories` list/detail, cursor, PAT mode) and CVE↔GHSA enrichment joins.
- [ ] Add NVD authenticated mode (`NVD_API_KEY`) and tune retry/backoff policy for sustained runs.
- [ ] Add stricter AI-relevance/product allowlist filtering for vuln-shaped candidate quality.

## Medium Priority

- [ ] Decide public surface for candidate output: labs docs, MCP-only, website, or another channel.
- [ ] Confirm redistribution boundaries for third-party advisory summaries and extracted text.
- [ ] Optional aidefend-mcp extension: namespaced candidate tools.
- [ ] Grow `lab/aidefend_discovery/gold/` from real gap reports to support quality checks.

## Resolved

- [x] Initialize safe repo-local `.ai` scaffold.
- [x] Phase 2A NVD connector baseline (anonymous mode + sqlite cursor) integrated into discovery pipeline.
- [x] Rename working identity to AIDEFEND Discovery in repo docs.
