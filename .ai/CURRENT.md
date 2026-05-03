# Current State

Updated: 2026-05-03 (full build-out: Phase 1 hygiene + Phase 2 bridge & anchor-diff + Phase 2A NVD auth + Phase 2B GHSA + Phase 3 sqlite/exports + Phase 4 MCP integration + Phase 5 governance + scheduler + gold corpus)

## Repo Purpose

**AIDEFEND Discovery** is a research and tooling workspace for finding, normalizing, scoring, and reviewing candidate additions or mappings for the AIDEFEND knowledge base.

## Current Status

- The repo has moved past the original empty security scaffold; its working identity is now **AIDEFEND Discovery**.
- `scripts/run_discovery_gap.py` supports `--source rss|nvd|ghsa`. NVD mode uses `scripts/aidefend_discovery/nvd_ingest.py` with `NVD_API_KEY` env auth + retry/backoff. GHSA mode uses `scripts/aidefend_discovery/ghsa_ingest.py` with `GH_PAT_FOR_GHSA` env auth + cursor pagination via Link headers. CVE↔GHSA join via `entities` sidecar.
- **CWE→tactic bridge** (`scripts/aidefend_discovery/bridge.py` + `lab/aidefend_discovery/bridges/cwe_to_tactic.yaml`, 26 CWEs with citations) populates `GapReport.bridge_rationales` / `suggested_*`.
- **Taxonomy anchor diff** (`scripts/anchor_diff.py` + 9 vendored YAMLs in `lab/aidefend_discovery/taxonomy_anchors/`) surfaces upstream framework IDs not yet mapped in AIDEFEND `defendsAgainst`.
- **sqlite candidate store** at `lab/aidefend_discovery/discovery_state.db` (state_store.py v1 schema: runs / candidates / gap_reports / seen_window) with `INSERT OR IGNORE` idempotency on `content_hash`. Read APIs power MCP + exports + metrics.
- **Review export + metrics**: `scripts/export_review.py` → CSV; `scripts/discovery_metrics.py` → JSON.
- **Scheduled run**: `.github/workflows/discovery-nightly.yml` (cron 09:00 UTC); secrets `NVD_API_KEY` + `GH_PAT_FOR_GHSA` provisioned. Auto-PR opened, never merged.
- **MCP integration** in `aidefend-mcp` repo: `app/discovery/store.py` + 3 namespace-walled tools (`search_discovery_candidates`, `explain_candidate_mapping`, `list_anchor_diff`). 14 contract tests asserting AID-* IDs only in `references_aid` sidecar.
- **Gold corpus**: 25 hand-labeled rows (19 covered / 6 gaps) in `lab/aidefend_discovery/gold/`. Eval baseline: is_gap_accuracy=0.76, nearest_topk_hit_rate=1.00, recall_is_gap=0.0 (embeddings re-open trigger fired).
- Existing enrichment/scoring remains: optional Trafilatura page fetch, candidate enrichment (`summary_raw`, `body_extracted`, chunks, entities), BM25 chunk max-pool, and lexical overlap explainability in gap reports.
- **Promotion path:** [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) gives the concrete `CandidateFinding` → upstream `tactics/*.js` shape mapping; Phase 1 exit now requires a merged upstream promotion PR. **Soft rule:** upstream promotions are paused until the Phase 2 taxonomy-anchor diff lands (avoids vocabulary drift from MITRE/OWASP/NIST anchors).
- **Research index:** [`docs/aidefend_discovery/discoveries/`](../docs/aidefend_discovery/discoveries/) (web extraction guidance; **NVD + GitHub global advisory REST** connector enumeration).
- No offensive targets, customer data, credentials, raw evidence, or proprietary security findings are tracked.
- Global continuity index may still route here for cross-repo R&D.

## Facts vs Assumptions

Facts:
- Discovery output is **candidate-only** until promoted in upstream aidefense-framework `tactics/*.js`.
- Phase 2A NVD baseline is implemented in anonymous mode; auth and GHSA are follow-on work.
- The local checkout is now `aidefend-discovery`; the GitHub remote may still be `minhh-le/persistent-agent-security` until the remote repository is renamed.

Needs definition later:
- Whether to rename the GitHub repository after the docs/local identity stabilizes.
- Public surface decision for candidate output: labs, MCP-only, website, or another channel.
- Redistribution rules for third-party advisory summaries beyond cited metadata.
