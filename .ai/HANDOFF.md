# Handoff

Updated: 2026-05-06 (canonical private monorepo consolidation in progress)
Updated by: Codex
Verification: `PYTHONPATH=scripts python3 -m unittest discover -s tests -v` (84 tests); `python3 scripts/export_review_digest.py --sample --output /tmp/aidefend_sample_digest.md --top-n 3`; no-network fixture replay against `vendor/aidefense-framework/data/data.json`; `python3 scripts/anchor_diff.py --output /tmp/aidefend_anchor_diff.json`; `cd review_console && npm test` (6 tests); `cd review_console && npm run build`; review-console API smoke against `tests/fixtures/sample_gap_run.json` on port 8766; `cd services/aidefend-mcp && .venv/bin/pytest tests/test_discovery_tools.py` (14 tests; configured/unconfigured discovery namespace coverage); from `../agent-continuity`, `python3 scripts/validate_continuity.py` (PASS) and `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` (PASS with expected pre-commit stale-handoff warning). Prior architecture build-out verification included live authenticated NVD + GHSA pulls and gold eval (is_gap_accuracy=0.76, nearest_topk_hit_rate=1.00).

## Current Goal

`main` is being consolidated into the canonical private monorepo. It contains
the discovery pipeline, public digest/review console, latest retained nightly
reports from `discovery-nightly/20260506`, a tracked AIDEFEND framework
snapshot under `vendor/aidefense-framework/`, and the full MCP/REST service
under `services/aidefend-mcp/`. The remaining work after consolidation is
**evaluation-driven precision tuning** plus **operationalisation**: first
promotion through the bundled framework snapshot, manual nightly review, and
credential rotation.

## Last Meaningful Work — monorepo consolidation (2026-05-06)

- Fast-forwarded local `main` to `origin/main@80ad177`.
- Merged `origin/cleanup/rename-and-consolidate@256b373`, preserving public
  review digest and local review console work.
- Merged latest useful nightly artifacts from
  `origin/discovery-nightly/20260506@b68d354` under `reports/auto/20260506/`.
  Older nightly branches contain earlier duplicate report sets and can be
  deleted once `main` is pushed.
- Imported plain-file snapshots:
  - `vendor/aidefense-framework/` from
    `edward-playground/aidefense-framework@e4d5659e03ac087f459350afde0e13161cdf2f93`
  - `services/aidefend-mcp/` from
    `minhh-le/aidefend-mcp@118c56cb8567ccc4eee9df1f766cb018be37963f`
- Added `vendor/SNAPSHOTS.md` and `docs/aidefend_discovery/MONOREPO.md`.
- Updated discovery defaults so `run_discovery_gap.py` and `anchor_diff.py`
  use `vendor/aidefense-framework/data/data.json` by default.
- Updated MCP service defaults so local service sync points at the bundled
  framework snapshot and report discovery points at root `reports/`.

## Last Meaningful Work — public demo review console (2026-05-05)

- Added `PRODUCT.md` design context for AIDEFEND Discovery as a product UI.
- Added `scripts/aidefend_discovery/review_console.py`.
  - Loads one `reports/gap_run_*.json` report and reuses
    `scripts/export_review_digest.py` scoring/action helpers.
  - Exposes local API endpoints for run metadata, candidate lists, candidate
    brief detail, decision save, reviewed list, reviewed-only Markdown export,
    and reviewed-only CSV export.
  - Stores review decisions in sqlite, keyed candidate-locally by
    `content_hash`, then `source_type + source_id`, then candidate/report
    fallback. Backend `recommended_action` remains separate from reviewer
    `review_decision`.
  - Serves the built React UI from `review_console/dist`.
- Added `review_console/` React + TypeScript + Vite app.
  - Three-pane laptop workbench: Review Queue, Candidate Brief, Decision Panel.
  - Queue tabs: Lowest Coverage, Highest Severity, Needs Evidence, Monitor,
    Reviewed.
  - Filters: source type, severity, coverage range, CWE, package ecosystem,
    reviewed/unreviewed.
  - Candidate brief shows human-readable sections first, with score/provenance
    collapsed by default and nearest-technique comparison inline.
  - Decision panel captures Promote, Merge Into Existing, Reject, Needs
    Evidence, Monitor plus owner, confidence, notes, merge/promotion fields,
    and future-ready disabled promotion actions.
- Added backend tests in `tests/test_review_console.py` and frontend tests in
  `review_console/src/App.test.tsx`.
- Documented run commands in `README.md` and `.ai/COMMANDS.md`.

## Last Meaningful Work — public review digest (2026-05-05)

- Added `scripts/export_review_digest.py`.
  - Input v1: one `reports/gap_run_*.json` file.
  - Output: Markdown digest with Run Summary, Lowest Coverage Candidates,
    Highest Severity Candidates, Candidate Briefs, and Methodology /
    Provenance appendix.
  - Scores: `Coverage Score: N/100` from `max_bm25 / gap_bm25_max`; `Security
    Score: N/100` from severity plus bounded evidence boosts.
  - Actions: `Promote`, `Merge Into Existing`, `Reject`, `Needs Evidence`,
    `Monitor`.
  - Raw provenance remains secondary in each brief: candidate ID, source type,
    source ID, retrieved timestamp, identifiers, source URLs, score details,
    gap reason, confidence, and license note.
- Added sample mode (`--sample`) backed by `tests/fixtures/sample_gap_run.json`
  for public testers without API credentials.
- Added `tests/test_review_digest.py` covering scoring, action recommendation,
  CLI rendering, `--top-n`, summary counts, table presence, deterministic
  timestamp behavior, sample mode, and candidate-brief de-duplication.
- Generated a real digest: `reports/discovery_digest_20260505.md`.
- Documented usage in `README.md`, `lab/aidefend_discovery/README.md`, and
  `.ai/COMMANDS.md`.

## Last Meaningful Work — cleanup closeout (2026-05-05)

- **GitHub repo renamed** `minhh-le/persistent-agent-security` → `minhh-le/aidefend-discovery` via `gh repo rename`. Local `origin` remote URL updated.
- **Loose docs consolidated:** `~/Desktop/repos/notes - aidefend discovery` moved into `docs/aidefend_discovery/NOTES.md`; `~/Desktop/repos/explanation of discovery.md` moved into `docs/aidefend_discovery/TECHNICAL_OVERVIEW.md`.
- **Stale `persistent-agent-security` references purged** from 7 active files (User-Agent strings in `rss_ingest.py`/`nvd_ingest.py`/`ghsa_ingest.py`/`audit_feeds.py`, `gh workflow run`/`gh secret set` examples in `lab/aidefend_discovery/README.md`, the workflow command in `.ai/OPEN_LOOPS.md`, and the rename-status fact in `.ai/CURRENT.md`). `.ai/SESSION_LOG.md` historical entries left intact as record of prior state.
- **Docs audit:** `docs/aidefend_discovery/ROADMAP.md`, `PROMOTION_PLAYBOOK.md`, `discoveries/INDEX.md`, `README.md`, `lab/aidefend_discovery/README.md`, and `.ai/*` reconciled with actual state — shipped Phase 1/2/3/4 items marked complete, anchor-diff pause lifted, active open loops preserved.
- **Global continuity routing:** `agent-continuity` now routes `aidefend-discovery` to `https://github.com/minhh-le/aidefend-discovery`.

## Prior Meaningful Work — full build-out (Blocks A→J)

- **Block A (Phase 1 hygiene):** version-range entity regex (CVE/GHSA-style
  prose); `NVD_API_KEY` auth + retry/backoff with jitter respecting Retry-After;
  `scripts/audit_feeds.py`; diversified feed allowlist (5 AI-stack feeds, 5/5
  reachable). Commit `4632242`.
- **Block C (Phase 3 data layer):** `state_store.py` v1 schema (runs /
  candidates / gap_reports / seen_window); idempotent `INSERT OR IGNORE`;
  `scripts/export_review.py` (CSV); `scripts/discovery_metrics.py` (JSON);
  `run_discovery_gap.py` writes sqlite alongside JSONL/JSON outputs. Drive-by
  fix: NVD reference dedup. Commit `82a0972`.
- **Block G (Phase 2B GHSA connector):** `scripts/aidefend_discovery/ghsa_ingest.py`
  mirrors NVD pattern; `GH_PAT_FOR_GHSA` Bearer auth; cursor pagination via
  Link header; CVE↔GHSA join via `entities`; `--source ghsa` route. Commit
  `09ed4e8`.
- **Block B (Phase 2 structural correlation):** `scripts/aidefend_discovery/bridge.py`
  + 26-CWE seed table at `lab/aidefend_discovery/bridges/cwe_to_tactic.yaml`
  with citations + per-entry confidence; `GapReport.bridge_rationales` field.
  `scripts/anchor_diff.py` + 9 vendored anchor YAMLs (MITRE ATLAS, OWASP
  LLM/ML/Agentic, NIST AI 100-2, MAESTRO, SAIF, Databricks DASF, Cisco AITech).
  Soft rule on `PROMOTION_PLAYBOOK.md` lifted. Bug fix in `extract.py`:
  preserve connector-supplied entities (was clobbering CWEs from GHSA).
  Commit `dc2db82`.
- **Block I (gold corpus):** 25 real hand-labeled rows (19 covered / 6 gaps)
  in `lab/aidefend_discovery/gold/`; eval upgraded with prefix matching +
  precision/recall/F1; current baseline `is_gap_accuracy=0.76`,
  `nearest_topk_hit_rate=1.00`, `recall_is_gap=0.0` — **embeddings re-open
  trigger fired**. Commit `d9e6b11`.
- **Block F (Phase 4 MCP integration):** now bundled under
  `services/aidefend-mcp/`: `app/discovery/store.py` (read-only sqlite client)
  + 3 namespace-walled tools (`search_discovery_candidates`,
  `explain_candidate_mapping`, `list_anchor_diff`). 14 contract tests assert
  AID-* IDs only appear in `references_aid` sidecar; every response carries
  `discovery_namespace: true` + disclaimer; graceful "not configured" when
  `DISCOVERY_DB_PATH` unset.
- **Blocks E + H (governance + scheduler):** `.github/PULL_REQUEST_TEMPLATE.md`
  + `discovery_promotion.md` specialised template;
  `docs/aidefend_discovery/QUALITY_AUDIT_CHECKLIST.md` 8-section quarterly
  ritual; `.github/workflows/discovery-nightly.yml` (NVD+GHSA+RSS+anchor diff
  +exports → auto-PR; never auto-merges). Repo secrets `NVD_API_KEY` +
  `GH_PAT_FOR_GHSA` provisioned via `gh secret set` from env (never echoed).

## Next Recommended Action

- **Open the first upstream promotion PR** to close the hardened Phase 1
  exit. Pick one row from `lab/aidefend_discovery/gold/labeling_log.md` Shape-A
  candidates (e.g., `GHSA-324q-cwx9-7crr` KubeAI command-injection → AID-H);
  walk it through `PROMOTION_PLAYBOOK.md`; consult anchor-diff for the
  framework you're touching.
- **Run the nightly workflow once manually**: `gh workflow run
  discovery-nightly.yml` and review the auto-PR's CSV/metrics.
- **Embeddings + cross-encoder rerank** (re-open trigger fired): with 25 gold
  rows and recall_is_gap=0.0 on out-of-scope detection, evaluate adding a
  scope classifier or cross-encoder rerank on BM25 top-20.
- **Refresh anchor YAMLs**: vendored snapshots are dated 2026-05-03; refresh
  per `QUALITY_AUDIT_CHECKLIST.md` Section 2 if upstream artifacts move.
- **Rotate credentials** that appeared in chat (`NVD_API_KEY`, `GH_PAT_FOR_GHSA`).

## Known Pitfalls

- Do not store secrets or raw sensitive evidence.
- Do not infer targets or scope.
- Do not run security tooling against third-party systems without explicit authorization.
- Do not treat discovery candidates as approved `AID-*` techniques without upstream merge.
