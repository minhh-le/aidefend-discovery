# Open Loops

Updated: 2026-05-02

## High Priority

- [ ] Define the first real security engineering line of effort.
- [ ] Define scope/authorization boundaries before any active testing.
- [ ] Decide evidence storage policy.

## Medium Priority

- [ ] **Implement GHSA connector** (`GET /advisories` list/detail, cursor, PAT mode) and CVE↔GHSA enrichment joins.
- [ ] Add NVD authenticated mode (`NVD_API_KEY`) and tune retry/backoff policy for sustained runs.
- [ ] Add stricter AI-relevance/product allowlist filtering for vuln-shaped candidate quality.
- [ ] Optional aidefend-mcp extension: namespaced candidate tools.
- [ ] Choose initial tooling/test stack for broader repo work.
- [ ] Add templates for findings and lab notes.

## Resolved

- [x] Initialize safe repo-local `.ai` scaffold.
- [x] Phase 2A NVD connector baseline (anonymous mode + sqlite cursor) integrated into discovery pipeline.
