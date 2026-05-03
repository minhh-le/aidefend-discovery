# Handoff

Updated: 2026-05-03 (architecture-edit session, full roadmap build-out: Blocks A→J)
Updated by: Claude Code (Opus 4.7)
Verification: `.venv/bin/python -m unittest discover -s tests -v` (59 tests, all pass — was 22); aidefend-mcp `pytest tests/test_discovery_tools.py` (14 tests pass); live authenticated NVD + GHSA pulls; gold eval (is_gap_accuracy=0.76, nearest_topk_hit_rate=1.00); from `../agent-continuity`: `python3 scripts/validate_continuity.py`, `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery`.

## Current Goal

Phases 1, 2A, 2B, 3, 4, 5 are now scaffolded end-to-end. The remaining work is
**evaluation-driven precision tuning** (embeddings + cross-encoder rerank, gated
on the gold-corpus precision plateau the eval just confirmed) plus
**operationalisation** (run the nightly workflow for a few cycles, do the first
upstream promotion PR via `PROMOTION_PLAYBOOK.md`, refresh vendored anchor
YAMLs quarterly).

## Last Meaningful Work — full build-out (Blocks A→J)

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
- **Block F (Phase 4 MCP integration):** in companion repo `aidefend-mcp`:
  `app/discovery/store.py` (read-only sqlite client) + 3 namespace-walled
  tools (`search_discovery_candidates`, `explain_candidate_mapping`,
  `list_anchor_diff`). 14 contract tests assert AID-* IDs only appear in
  `references_aid` sidecar; every response carries
  `discovery_namespace: true` + disclaimer; graceful "not configured" when
  `DISCOVERY_DB_PATH` unset. Locally committed (no push to upstream Edward
  Lee repo per the "pause before upstream PRs" memory).
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
