# Session Log

## 2026-04-30 — Scaffold initialized

Summary:
Created safe initial repo-local `.ai` packet and placeholder directories for persistent agent security work.

Changed:
- Added README, AGENTS, `.ai` continuity files, safety-focused `.gitignore`, and placeholder directories.

Next:
- Define first real security objective and scope.

## 2026-05-01 — AIDEFEND discovery slice

Summary:
Implemented baseline flattening from aidefense-framework `data.json`, BM25 retrieval, allowlisted RSS/Atom ingestion, gap report CLI, unit tests, and documentation (`docs/aidefend_discovery/*`, `.ai` updates).

Changed:
- Added `scripts/aidefend_discovery/`, `scripts/run_discovery_gap.py`, `tests/`, `lab/aidefend_discovery/feeds.allowlist`, gitignore entries for generated candidates/reports.

Next:
- Tune gap thresholds per feed; optional MCP extension; founder confirmation on CC BY boundaries for candidate summaries.

## 2026-05-02 — Discovery roadmap (persistent doc)

Summary:
Authored [docs/aidefend_discovery/ROADMAP.md](docs/aidefend_discovery/ROADMAP.md) (phases 0–5, end-state definition) and linked it from README, CONTEXT_INDEX, and lab README.

Changed:
- Added `docs/aidefend_discovery/ROADMAP.md`; updated `.ai/CONTEXT_INDEX.md`, `README.md`, `lab/aidefend_discovery/README.md`.

Next:
- Execute Phase 1 items from the roadmap when prioritizing discovery work.

## 2026-05-02 — Roadmap action items + discover synthesis

Summary:
Expanded [docs/aidefend_discovery/ROADMAP.md](docs/aidefend_discovery/ROADMAP.md) with per-phase checklists and linked [docs/aidefend_discovery/discoveries/](docs/aidefend_discovery/discoveries/) (web extraction pipeline research: Trafilatura-first vs crawl4ai).

Changed:
- Added `docs/aidefend_discovery/discoveries/INDEX.md`, `2026-05-02-web-extraction-pipeline.md`; updated CONTEXT_INDEX and lab README.

Next:
- Run full `/discover` + `/codex` when ready for NVD/GitHub Advisory primary-source sweep; append new discovery row.

## 2026-05-02 — Phase 1 (Trafilatura, no crawl4ai)

Summary:
Implemented Trafilatura page fetch (host allowlist), dual-field candidates, chunked max-pooled BM25, CVE/GHSA/CWE extraction, lexical overlap explainability, `requirements.txt` + venv-friendly commands, gold eval scaffold.

Changed:
- Added `scripts/aidefend_discovery/{extract,entities,explain}.py`, `requirements.txt`, `lab/.../page_fetch.allowlist`, `lab/.../gold/`, `scripts/eval_discovery_gold.py`; extended `run_discovery_gap.py`, `bm25_index.py`, tests, ROADMAP Phase 1 checkboxes, COMMANDS.

Next:
- Label `gold/*.jsonl` from real `gap_run` output; grow NVD/GitHub connectors (Phase 2).

## 2026-05-02 — Discover: NVD + GitHub advisory API enumeration

Summary:
Host-side `/discover`-style pass over official NVD CVE 2.0 and GitHub global security advisory REST docs; wrote [docs/aidefend_discovery/discoveries/2026-05-02-nvd-ghsa-connector-api.md](docs/aidefend_discovery/discoveries/2026-05-02-nvd-ghsa-connector-api.md) and indexed it.

Changed:
- `docs/aidefend_discovery/discoveries/*`, ROADMAP Phase 1 discover checkbox.

Next:
- Implement Phase 2 connectors C1/C4/C5 using env keys; optional Codex `crwl` pass for changelog-only deltas not in REST.

## 2026-05-02 — Session closeout

Summary:
Aligned `.ai` HANDOFF/CURRENT/OPEN_LOOPS/DECISIONS/CONTEXT_INDEX; registered **agent-continuity** effort `aidefend-discovery-mesh` + updated **GLOBAL_INDEX** for `persistent-agent-security`; `python3 scripts/validate_continuity.py` in agent-continuity → **PASS** (3 efforts). Committed and pushed: **persistent-agent-security** `804502b`, **agent-continuity** `285f2e3`.

Next:
- Phase 2 connector implementation + gold labels (see HANDOFF).

## 2026-05-02 — Phase 2A NVD connector implementation

Summary:
Implemented Phase 2A NVD connector baseline end-to-end: source dispatch in `run_discovery_gap.py`, NVD incremental ingest/normalization module, sqlite cursor state store, compatibility tests, and operator docs.

Changed:
- Added `scripts/aidefend_discovery/nvd_ingest.py` and `scripts/aidefend_discovery/state_store.py`.
- Extended `scripts/run_discovery_gap.py` with `--source nvd`, NVD args, cursor-backed window defaults, and source metadata in report params.
- Added tests `tests/test_nvd_connector.py`, `tests/test_state_store.py`, and NVD flow/orchestration coverage in `tests/test_aidefend_discovery.py`.
- Updated docs: `lab/aidefend_discovery/README.md`, `docs/aidefend_discovery/ROADMAP.md`, `docs/aidefend_discovery/discoveries/INDEX.md`.
- Updated continuity packet: `HANDOFF`, `CURRENT`, `OPEN_LOOPS`, `DECISIONS`.

Verification:
- `PYTHONPATH=scripts .venv/bin/python -m unittest tests.test_nvd_connector -v`
- `PYTHONPATH=scripts .venv/bin/python -m unittest tests.test_state_store -v`
- `PYTHONPATH=scripts .venv/bin/python -m unittest tests.test_aidefend_discovery.TestRunDiscoveryOrchestration.test_source_nvd_dispatch -v`
- `PYTHONPATH=scripts .venv/bin/python -m unittest tests.test_aidefend_discovery.TestNvdFlowCompatibility -v`
- `PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v`
- `python3 scripts/run_discovery_gap.py --help`

Next:
- Implement Phase 2B GHSA connector + CVE↔GHSA joins.
- Add NVD auth path and stronger ingestion retry/rate-limit policy tuning.

## 2026-05-03 — Architecture-edit session: full roadmap build-out (Blocks A→J)

Summary:
End-to-end implementation of the remaining roadmap. User authorized full-scope
work with credentials in-band (NVD_API_KEY + GH_PAT_FOR_GHSA), the upstream
`aidefend-mcp` repo in scope, and `/discover` available. Eight execution
blocks (A through J) shipped as per-theme commits with passing tests.

Changed (this repo, in commit order):
- `4632242` Block A: NVD auth + version-range entities + feed audit script.
  Diversified `feeds.allowlist` to 5 AI-stack feeds (LangChain, vLLM,
  LlamaIndex, Open-WebUI, AutoGPT — all 200/reachable). Page-fetch allowlist
  added nvd.nist.gov + huntr + snyk hosts.
- `82a0972` Block C: state_store v1 schema (runs/candidates/gap_reports/
  seen_window) + INSERT OR IGNORE idempotency keyed on content_hash;
  `scripts/export_review.py` (CSV) + `scripts/discovery_metrics.py` (JSON);
  `run_discovery_gap.py` writes sqlite alongside JSONL. Drive-by fix: dedupe
  NVD reference URLs (NVD returns each twice when tags differ).
- `09ed4e8` Block G: GHSA connector (`scripts/aidefend_discovery/ghsa_ingest.py`)
  with PAT auth via `GH_PAT_FOR_GHSA`/`GITHUB_TOKEN` fallback; cursor
  pagination via Link header `rel="next"`; CVE↔GHSA join. `--source ghsa`
  route + 5 new GHSA-specific CLI flags.
- `dc2db82` Block B: CWE→tactic bridge (26 seeded CWEs with citations + per-
  entry confidence in `lab/aidefend_discovery/bridges/cwe_to_tactic.yaml`);
  `GapReport.bridge_rationales` field. Taxonomy anchor diff (`scripts/anchor_diff.py`)
  + 9 vendored anchor YAMLs (MITRE ATLAS / OWASP LLM/ML/Agentic / NIST AI
  100-2 / MAESTRO / SAIF / DASF / Cisco AITech). Soft promotion-pause rule
  in `PROMOTION_PLAYBOOK.md` lifted. Bug fix in `extract.py`: connector-
  supplied entities (e.g., GHSA CWE list) now MERGE into text-extracted
  entities instead of being clobbered.
- `d9e6b11` Block I: 25 hand-labeled gold rows
  (`lab/aidefend_discovery/gold/example_labels.jsonl`) — 19 covered / 6 gaps;
  `eval_discovery_gold.py` upgraded with prefix matching + precision/recall/
  F1; `labeling_log.md` per-row audit table.
- This commit (Blocks E + H): `.github/PULL_REQUEST_TEMPLATE.md` + specialised
  `discovery_promotion.md`; `docs/aidefend_discovery/QUALITY_AUDIT_CHECKLIST.md`
  8-section quarterly ritual; `.github/workflows/discovery-nightly.yml`
  (cron 09:00 UTC; opens auto-PR, never auto-merges); secrets `NVD_API_KEY`
  and `GH_PAT_FOR_GHSA` provisioned via `gh secret set` (values piped from
  env, never echoed).

Changed (companion repo `aidefend-mcp`, locally committed only):
- `app/discovery/{__init__,store}.py` — read-only sqlite client with
  AID-* sidecar enforcement.
- `app/tools/{search_discovery_candidates,explain_candidate_mapping,list_anchor_diff}.py`
  — three namespace-walled tools.
- `app/config.py` — `DISCOVERY_DB_PATH` + `DISCOVERY_REPORTS_PATH`
  Optional[Path] fields.
- `mcp_server.py` — register Tool definitions + dispatch.
- `tests/test_discovery_tools.py` — 14 contract tests asserting AID-* IDs
  only in `references_aid` sidecar; every response carries
  `discovery_namespace: true` + disclaimer; graceful "not configured" when
  unset.

Verification:
- `aidefend-discovery`: 59/59 unit tests pass (was 22 → 30 → 35 → 45 → 54 → 59
  across the blocks). Live authenticated NVD pull (10 CVEs in 4.2s) and
  GHSA pull (10 advisories with 5 CVEs + 10 CWEs); end-to-end with sqlite
  store + bridge_rationales populated for 5/6 GHSA candidates; anchor diff
  surfaces 40 regression candidates across 9 frameworks; gold eval
  is_gap_accuracy=0.76, nearest_topk_hit_rate=1.00, recall_is_gap=0.0.
- `aidefend-mcp`: 14/14 discovery contract tests pass; 305 pre-existing unit
  tests still pass; 2 unrelated pre-existing failures
  (test_defenses_for_threat_fix) require populated LanceDB sync.
- Workflow YAML parses cleanly (15 steps); `gh secret list` shows
  `NVD_API_KEY` + `GH_PAT_FOR_GHSA` present on
  `minhh-le/persistent-agent-security`.
- Closeout validators (run from `../agent-continuity`):
  `closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` PASS;
  `validate_continuity.py` PASS.

Next:
- Open the first upstream promotion PR per `PROMOTION_PLAYBOOK.md` to close
  the hardened Phase 1 exit. Recommended candidate: `GHSA-324q-cwx9-7crr`
  (KubeAI command injection → AID-H Shape-A).
- Run `gh workflow run discovery-nightly.yml` once manually, review auto-PR.
- Evaluate embeddings + cross-encoder rerank (re-open trigger fired:
  `recall_is_gap=0.0` on out-of-scope gap detection).
- **User: rotate `NVD_API_KEY` and `GH_PAT_FOR_GHSA` that appeared in chat
  transcripts**; update GH secrets after rotation.

## 2026-05-02 — Architecture-edit session: promotion playbook + Phase 1 exit hardening

Summary:
Architecture review of [`docs/aidefend_discovery/ROADMAP.md`](../docs/aidefend_discovery/ROADMAP.md) and the [notes file](../../notes%20-%20aidefend%20discovery). Found no blatant wrongs in the roadmap; identified the promotion playbook as the one fix-now (bottleneck for Phase 1 exit) and codified the rest as "Deferred with reasoning" with explicit re-open triggers. Also caught and fixed stale `persistent-agent-security-discovery/*` HTTP User-Agent strings in two ingestion modules left over from before the repo rename.

Changed:
- Added `docs/aidefend_discovery/PROMOTION_PLAYBOOK.md` — pre-flight checks, Shape A vs Shape B, tactic-letter table (M/H/D/I/DV/E/R), `CandidateFinding`→technique crosswalk, schema-gap callouts, PR template, smoke-test step, soft rule pausing promotions until Phase 2 taxonomy-anchor diff lands.
- Updated `docs/aidefend_discovery/ROADMAP.md`: Phase 1 exit now requires a merged upstream promotion PR (not just a renderable demo); new Phase 1 action item linking the playbook; Phase 2 anchor-diff line annotated as the prerequisite for resuming promotions; new "Deferred with reasoning" section listing six items with re-open triggers (is_gap two-trigger noise, BM25 vuln-shape mismatch, license posture, taxonomy drift, BM25 field weighting, body cap/chunk budget).
- Updated `.ai/DECISIONS.md`: 2026-05-02 entry recording playbook authorship + hardened exit + deferral decisions + soft rule.
- Updated `.ai/CONTEXT_INDEX.md`, `.ai/CURRENT.md`, `.ai/HANDOFF.md`, `.ai/OPEN_LOOPS.md` to reflect the new playbook and hardened exit.
- Fixed `scripts/aidefend_discovery/rss_ingest.py` and `scripts/aidefend_discovery/nvd_ingest.py` HTTP User-Agent strings: project identity now `aidefend-discovery/X.Y` with the actual `minhh-le/persistent-agent-security` remote URL (was placeholder `example.com` + old project slug).

Verification:
- `.venv/bin/python -m unittest discover -s tests -v` → 22 tests pass (UA changes do not affect test fixtures).
- `git diff --stat` → docs + two `.py` UA-string lines + `.ai/` packet, no unintended scope.
- From `../agent-continuity`: `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` and `python3 scripts/validate_continuity.py` (run at closeout below).

Next:
- Open the first upstream promotion PR per `PROMOTION_PLAYBOOK.md` to close the hardened Phase 1 exit; this stress-tests `CandidateFinding` for promotion-time data sufficiency.
- Begin Phase 2 taxonomy-anchor diff (prerequisite for resuming routine promotions; blocks vocabulary drift).
- Continue Phase 2B GHSA connector + CVE↔GHSA joins; NVD auth mode follow-up.

## 2026-05-02 — Rename and continuity cleanup

Summary:
Renamed the repo's working identity to **AIDEFEND Discovery** in user-facing docs and pruned stale `.ai` placeholder loops that no longer matched the active discovery work.

Changed:
- Updated `README.md`, `AGENTS.md`, `.ai/CONTEXT_INDEX.md`, `.ai/CURRENT.md`, `.ai/HANDOFF.md`, `.ai/OPEN_LOOPS.md`, `.ai/DECISIONS.md`, `.ai/COMMANDS.md`, `.ai/FINDINGS_INDEX.md`, and `.ai/THREAT_MODEL.md`.
- Replaced the placeholder threat model with a discovery-specific risk model for public source ingestion, candidate records, API tokens, and overclaiming risk.
- Updated dated discovery note context lines to use AIDEFEND Discovery as the project name.
- Updated local checkout references to `aidefend-discovery` and ignored generated `lab/aidefend_discovery/discovery_state.db`.

Verification:
- `git diff --check`
- `PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v` (22 tests)
- `python3 scripts/validate_continuity.py` from `../agent-continuity`
- `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` from `../agent-continuity`

Next:
- Continue Phase 2B GHSA connector work.
- Decide later whether to rename the GitHub repo after the docs/local identity stabilizes.

## 2026-05-03 PM — Repo rename + notes consolidation + doc audit

Summary:
Closed the long-standing "decide later" item from 2026-05-02: renamed the GitHub repo to match the local identity, pulled the loose architecture-sketch notes file into the repo, and audited docs against the actual Phase 1–5 build-out so the roadmap and README stop claiming work that already shipped is upcoming.

Changed:
- `gh repo rename minhh-le/persistent-agent-security` → `aidefend-discovery`; updated local `origin` URL.
- Moved `~/Desktop/repos/notes - aidefend discovery` → `docs/aidefend_discovery/NOTES.md` with a status banner pointing readers to current state, and updated the historical "prototype home" line from a question to the decided answer.
- Replaced `persistent-agent-security` references in 7 active files: User-Agent strings in `scripts/aidefend_discovery/{rss,nvd,ghsa}_ingest.py` + `scripts/audit_feeds.py`; `gh workflow run` / `gh secret set` examples in `lab/aidefend_discovery/README.md`; the workflow command in `.ai/OPEN_LOOPS.md`; and the rename-status fact in `.ai/CURRENT.md`. Historical `.ai/SESSION_LOG.md` entries left intact as factual record.
- Audited `docs/aidefend_discovery/ROADMAP.md`: flipped Phase 1 promotion-playbook checkbox; flipped Phase 2 NVD-auth + GHSA checkboxes; flipped Phase 3 sqlite/idempotency/scheduler/export/metrics checkboxes (all shipped); flipped Phase 4 MCP-tools + contract-tests checkboxes; annotated embeddings entry with the fired re-open trigger from the gold eval; marked taxonomy-drift deferral resolved (anchor diff shipped); updated header date.
- Rewrote `README.md` "Scope" section so it reflects shipped state (NVD+GHSA auth, bridges, anchor diff, sqlite, exports, scheduler, MCP) instead of describing Phase 2 as upcoming.
- Reviewed `MAINTAINER_ALIGNMENT.md`, `REVIEW_CONTRACT.md`, `PROMOTION_PLAYBOOK.md`, `QUALITY_AUDIT_CHECKLIST.md` — already aligned with current state, no edits needed.

Verification:
- `python3 scripts/validate_continuity.py` from `../agent-continuity` (PASS)
- `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` from `../agent-continuity`
- `.venv/bin/python -m unittest discover -s tests` after the User-Agent string changes
- `git ls-remote origin HEAD` after remote URL change (resolves)

Next:
- Push branch `cleanup/rename-and-consolidate` (paused per "pause before upstream PRs" — confirm with user first).
- Open the first upstream promotion PR per `PROMOTION_PLAYBOOK.md` (high-priority open loop).
- Run nightly workflow once manually, review auto-PR exports.

## 2026-05-05 — Codex cleanup closeout + cross-repo sync

Summary:
Finished the interrupted cleanup session: consolidated the remaining loose technical overview into the repo, aligned active docs with the shipped Phase 1-5 state, and synced `agent-continuity` routing to the renamed GitHub repository.

Changed:
- Moved `~/Desktop/repos/explanation of discovery.md` → `docs/aidefend_discovery/TECHNICAL_OVERVIEW.md`.
- Updated `PROMOTION_PLAYBOOK.md` and `.ai/CURRENT.md` to say promotions are allowed after the required anchor-diff pre-flight; removed active wording that implied promotions were still paused.
- Updated `README.md`, `lab/aidefend_discovery/README.md`, `.ai/CONTEXT_INDEX.md`, `.ai/COMMANDS.md`, `.ai/DECISIONS.md`, `.ai/HANDOFF.md`, `.ai/OPEN_LOOPS.md`, and `docs/aidefend_discovery/discoveries/INDEX.md` so shipped NVD/GHSA/sqlite/export/metrics/scheduler/MCP/anchor-diff state and open work agree.
- Updated `agent-continuity` global routing files so `aidefend-discovery` points at `https://github.com/minhh-le/aidefend-discovery`.

Verification:
- `python3 scripts/validate_continuity.py` from `../agent-continuity`
- `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` from `../agent-continuity`
- `.venv/bin/python -m unittest discover -s tests -v`
- `gh repo view minhh-le/aidefend-discovery --json name,url`

Next:
- Open the first upstream promotion PR per `PROMOTION_PLAYBOOK.md`.
- Run the nightly workflow manually once and review the auto-PR exports.
- Continue embeddings + cross-encoder rerank evaluation after the `recall_is_gap=0.0` gold-corpus trigger.
