# Current State

Updated: 2026-05-08 (public local-demo product conversion)

## Repo Purpose

**AIDEFEND Discovery** is the canonical private monorepo for finding,
normalizing, scoring, reviewing, and serving AIDEFEND candidate additions or
mappings alongside tracked AIDEFEND framework and MCP/REST snapshots.

## Current Status

- The repo has moved past the original empty security scaffold; its working identity is now **AIDEFEND Discovery**.
- `main` is the canonical private monorepo and now carries the discovery
  pipeline, public digest/review console work, clone-and-run local demo
  product shell, latest useful 20260506 nightly artifacts,
  `vendor/aidefense-framework/`, and `services/aidefend-mcp/`.
- **Public local demo product:** `make demo` / `python3 scripts/run_demo.py`
  starts the local product, builds the React console, starts the Python API,
  opens a browser, and defaults to the checked-in sample report.
- `scripts/run_discovery_gap.py` and `scripts/anchor_diff.py` default to
  `vendor/aidefense-framework/data/data.json`.
- `scripts/run_discovery_gap.py` supports `--source rss|nvd|ghsa`. NVD mode uses `scripts/aidefend_discovery/nvd_ingest.py` with `NVD_API_KEY` env auth + retry/backoff. GHSA mode uses `scripts/aidefend_discovery/ghsa_ingest.py` with `GH_PAT_FOR_GHSA` env auth + cursor pagination via Link headers. CVE↔GHSA join via `entities` sidecar.
- **CWE→tactic bridge** (`scripts/aidefend_discovery/bridge.py` + `lab/aidefend_discovery/bridges/cwe_to_tactic.yaml`, 26 CWEs with citations) populates `GapReport.bridge_rationales` / `suggested_*`.
- **Taxonomy anchor diff** (`scripts/anchor_diff.py` + 9 vendored YAMLs in `lab/aidefend_discovery/taxonomy_anchors/`) surfaces upstream framework IDs not yet mapped in AIDEFEND `defendsAgainst`.
- **sqlite candidate store** at `lab/aidefend_discovery/discovery_state.db` (state_store.py v1 schema: runs / candidates / gap_reports / seen_window) with `INSERT OR IGNORE` idempotency on `content_hash`. Read APIs power MCP + exports + metrics.
- **Review export + metrics**: `scripts/export_review.py` → CSV; `scripts/discovery_metrics.py` → JSON.
- **Public review digest**: `scripts/export_review_digest.py` renders deterministic Markdown from a single `reports/gap_run_*.json`, with lowest-coverage/highest-severity tables, candidate briefs, numeric coverage/security scores, reviewer action labels, and raw provenance in each brief. `--sample` uses `tests/fixtures/sample_gap_run.json` so public testers can preview the format without API keys.
- **Public demo review console/product UI**:
  `scripts/aidefend_discovery/review_console.py` + `review_console/` provide a
  local Python API and React/TypeScript mission-control interface. It can load
  the sample report or start new discovery runs from UI presets: RSS, NVD,
  GHSA, or Full Sweep merged queue. It reuses digest scoring/action helpers,
  stores reviewer decisions candidate-locally in sqlite, keeps backend
  `recommended_action` separate from reviewer `review_decision`, supports run
  lifecycle logs/errors, source health, queue tabs/filters, layman-readable
  briefs, expert evidence/provenance expansion, optional on-demand AI summaries
  with deterministic fallback, and reviewed-only/full-run/Action Packet exports.
- **Scheduled run**: `.github/workflows/discovery-nightly.yml` (cron 09:00 UTC); secrets `NVD_API_KEY` + `GH_PAT_FOR_GHSA` provisioned. Auto-PR opened, never merged.
- **MCP/REST integration** is bundled in `services/aidefend-mcp/`: full service
  snapshot plus `app/discovery/store.py` and 3 namespace-walled tools
  (`search_discovery_candidates`, `explain_candidate_mapping`,
  `list_anchor_diff`). 14 contract tests assert AID-* IDs only in
  `references_aid` sidecar.
- **Gold corpus**: 25 hand-labeled rows (19 covered / 6 gaps) in `lab/aidefend_discovery/gold/`. Eval baseline: is_gap_accuracy=0.76, nearest_topk_hit_rate=1.00, recall_is_gap=0.0 (embeddings re-open trigger fired).
- Existing enrichment/scoring remains: optional Trafilatura page fetch, candidate enrichment (`summary_raw`, `body_extracted`, chunks, entities), BM25 chunk max-pool, and lexical overlap explainability in gap reports.
- **Promotion path:** [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) gives the concrete `CandidateFinding` → upstream `tactics/*.js` shape mapping; Phase 1 exit now requires a merged upstream promotion PR. The Phase 2 taxonomy anchor diff has shipped, so promotions are allowed after the required anchor-diff pre-flight.
- **Research index:** [`docs/aidefend_discovery/discoveries/`](../docs/aidefend_discovery/discoveries/) (web extraction guidance; **NVD + GitHub global advisory REST** connector enumeration).
- No offensive targets, customer data, credentials, raw evidence, or proprietary security findings are tracked.
- Global continuity index routes here for this durable product/R&D effort.

## Facts vs Assumptions

Facts:
- Discovery output is **candidate-only** until promoted through an explicit
  framework tactic edit under `vendor/aidefense-framework/tactics/*.js` and
  regenerated `vendor/aidefense-framework/data/data.json`.
- Imported snapshots are tracked in `vendor/SNAPSHOTS.md`:
  `edward-playground/aidefense-framework@e4d5659e03ac087f459350afde0e13161cdf2f93`
  and `minhh-le/aidefend-mcp@118c56cb8567ccc4eee9df1f766cb018be37963f`.
- NVD ingest is authenticated (`NVD_API_KEY` + retry/backoff); GHSA ingest is authenticated (`GH_PAT_FOR_GHSA` + cursor pagination).
- Optional AI summaries are provider-agnostic and demo-only. OpenRouter works
  through `AI_SUMMARY_BASE_URL`, `AI_SUMMARY_API_KEY`, `AI_SUMMARY_MODEL`, or a
  session-only pasted key in the UI. Core product functionality does not depend
  on AI.
- Local checkout and GitHub remote are both `aidefend-discovery` — repository was renamed from `persistent-agent-security` on 2026-05-03.
- Loose architecture-sketch notes were consolidated into `docs/aidefend_discovery/NOTES.md` on 2026-05-03 (was `~/Desktop/repos/notes - aidefend discovery`).
- Loose technical overview was consolidated into `docs/aidefend_discovery/TECHNICAL_OVERVIEW.md` on 2026-05-05 (was `~/Desktop/repos/explanation of discovery.md`).

Needs definition later:
- Whether/when to deploy beyond clone-and-run local demo.
- Redistribution rules for third-party advisory summaries beyond cited metadata.
