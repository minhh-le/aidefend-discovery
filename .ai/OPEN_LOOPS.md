# Open Loops

Updated: 2026-05-03 (full build-out: Blocks A→J of the architecture-edit session)

## High Priority

- [ ] **Open the first upstream promotion PR** per [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) to close the hardened Phase 1 exit. Use a Shape-A candidate from `lab/aidefend_discovery/gold/labeling_log.md` (e.g., `GHSA-324q-cwx9-7crr` KubeAI command-injection).
- [ ] **Run the nightly workflow once manually** (`gh workflow run discovery-nightly.yml --repo minhh-le/persistent-agent-security`) and review the auto-PR's exports.
- [ ] **Embeddings + cross-encoder rerank** — re-open trigger fired (gold `recall_is_gap=0.0`); evaluate adding a scope classifier or rerank on BM25 top-20.
- [ ] **Rotate credentials**: revoke and re-issue `NVD_API_KEY` and `GH_PAT_FOR_GHSA` that appeared in chat transcripts. Update `gh secret set` after rotation.
- [ ] Add stricter AI-relevance/product allowlist filtering for vuln-shaped candidate quality (intersects with embeddings rerank).

## Medium Priority

- [ ] Decide public surface for candidate output: labs docs, MCP-only, website, or another channel. License-posture upgrade gated on this (see ROADMAP "Deferred with reasoning" license-posture re-open trigger).
- [ ] Refresh vendored taxonomy anchor YAMLs (`lab/aidefend_discovery/taxonomy_anchors/`) per `QUALITY_AUDIT_CHECKLIST.md` Section 2 — quarterly.
- [ ] Grow `lab/aidefend_discovery/gold/example_labels.jsonl` from 25 → 50+ rows; unlocks BM25 field-weighting work.
- [ ] Push `aidefend-mcp` Block-F changes upstream (locally committed, awaiting smoke test + PR copy steering).

## Resolved this session (2026-05-03)

- [x] Block A: Phase 1 hygiene + NVD auth (commit `4632242`).
- [x] Block C: sqlite candidate store + idempotency + export (commit `82a0972`).
- [x] Block G: GHSA connector (commit `09ed4e8`).
- [x] Block B: CWE→tactic bridge + taxonomy anchor diff (commit `dc2db82`).
- [x] Block I: 25-row gold corpus + eval upgrade (commit `d9e6b11`).
- [x] Block F: MCP discovery tools in `aidefend-mcp` (locally committed; not pushed).
- [x] Blocks E + H: governance templates + nightly scheduler workflow + secret provisioning.

## Resolved earlier

- [x] Initialize safe repo-local `.ai` scaffold.
- [x] Phase 2A NVD connector baseline (anonymous mode + sqlite cursor) integrated into discovery pipeline.
- [x] Rename working identity to AIDEFEND Discovery in repo docs.
- [x] Author [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md); harden Phase 1 exit to require merged upstream PR; add ROADMAP "Deferred with reasoning" section with re-open triggers.
- [x] Fix stale `persistent-agent-security-discovery/*` User-Agent strings in `rss_ingest.py` / `nvd_ingest.py`.
