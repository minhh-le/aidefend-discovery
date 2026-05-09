# Open Loops

Updated: 2026-05-09 (review-console quality gate hardening)

## High Priority

- [ ] **Run a real-key demo rehearsal**: `make demo`; configure OpenRouter
  model/key via env or session-only UI field; run the curated demo, live
  advisory scan, and broad source sweep with appropriate keys; verify AI
  success path, fallback path, quality guidance, logs, reviewed-only exports,
  full-run exports, and Action Packet output in-browser.
- [ ] **Open the first upstream promotion PR** per [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) to close the hardened Phase 1 exit. Use a Shape-A candidate from `lab/aidefend_discovery/gold/labeling_log.md` (e.g., `GHSA-324q-cwx9-7crr` KubeAI command-injection).
- [ ] **Run the nightly workflow once manually** (`gh workflow run discovery-nightly.yml --repo minhh-le/aidefend-discovery`) and review the auto-PR's exports.
- [ ] **Embeddings + cross-encoder rerank** — re-open trigger fired (gold `recall_is_gap=0.0`); evaluate adding a scope classifier or rerank on BM25 top-20.
- [ ] **Rotate credentials**: revoke and re-issue `NVD_API_KEY` and `GH_PAT_FOR_GHSA` that appeared in chat transcripts. Update `gh secret set` after rotation.
- [ ] Continue stricter AI-relevance/product allowlist filtering beyond the
  deterministic review-console quality gate (intersects with embeddings rerank).
- [ ] After monorepo validation is pushed to `main`, delete fully represented
  remote branches: `cleanup/rename-and-consolidate`,
  `discovery-nightly/20260504`, `discovery-nightly/20260505`, and
  `discovery-nightly/20260506`.

## Medium Priority

- [ ] Decide whether/when to deploy beyond clone-and-run local demo. License-posture upgrade gated on this (see ROADMAP "Deferred with reasoning" license-posture re-open trigger).
- [ ] Refresh vendored taxonomy anchor YAMLs (`lab/aidefend_discovery/taxonomy_anchors/`) per `QUALITY_AUDIT_CHECKLIST.md` Section 2 — quarterly.
- [ ] Grow `lab/aidefend_discovery/gold/example_labels.jsonl` from 25 → 50+ rows; unlocks BM25 field-weighting work.

## Resolved this session (2026-05-09 review-console quality gate hardening)

- [x] Formalized a quality lifecycle for discovery rows: `raw_source_item`,
  `normalized_candidate`, `needs_enrichment`, `review_ready`, and `low_signal`.
- [x] Reworked first-screen IA around `Run curated demo`, `Run live advisory
  scan`, and `Run broad source sweep`; RSS release-note collection is no longer
  presented as quick scan value.
- [x] Replaced the synthetic sample with real GHSA/NVD-style evidence and
  deterministic golden-quality candidate narratives.
- [x] Default queue excludes low-signal release noise and shows only
  review-ready candidates; needs-enrichment and low-signal rows remain available
  through explicit navigation.
- [x] Added live advisory guidance when GHSA/NVD produces fewer than three
  review-ready candidates.
- [x] Made review-ready require meaningful attack/vulnerability prose and moved
  score mechanics into provenance.
- [x] Fixed stale selected-candidate state on new run start/report changes.
- [x] Added run summary counts and backend/frontend/digest tests for the quality
  split.

## Resolved earlier (2026-05-08 public local-demo product conversion)

- [x] Added one-command local startup (`make demo`, `scripts/run_demo.py`) with
  frontend build, Python API start, open-port selection, and browser auto-open.
- [x] Converted the review console into a mission-control product UI with dark
  threat-intel aesthetic, source health, trust posture, run presets, run logs,
  errors, candidate review, optional AI briefing, and exports.
- [x] Added UI-run presets for sample, RSS, NVD, GHSA, and Full Sweep merged
  queue.
- [x] Added provider-agnostic optional AI summary support with deterministic
  fallback and no persistent key/output storage.
- [x] Split reviewed-only exports from full-run exports and added selected
  candidate Action Packets.
- [x] Added demo runbook and future-work roadmap.
- [x] Ignored generated local demo DB/report artifacts.

## Resolved this session (2026-05-06 monorepo consolidation)

- [x] Fast-forwarded `main` to `origin/main@80ad177`.
- [x] Merged `cleanup/rename-and-consolidate@256b373` into `main`.
- [x] Preserved latest useful nightly artifacts from
  `discovery-nightly/20260506@b68d354`.
- [x] Imported `vendor/aidefense-framework/` from upstream commit `e4d5659`.
- [x] Imported `services/aidefend-mcp/` from fork commit `118c56c`.
- [x] Added monorepo snapshot manifest and root docs/commands wiring.

## Resolved this session (2026-05-05 public demo review console)

- [x] Added local Public Demo Console API for one `gap_run_*.json` report with candidate list/detail, decision save, reviewed list, and reviewed-only Markdown/CSV exports.
- [x] Added candidate-local sqlite review persistence keyed by `content_hash`, then `source_type + source_id`, then candidate/report fallback.
- [x] Added React + TypeScript three-pane review workbench with queue tabs, filters, human-readable brief, collapsed provenance, nearest-technique comparison, decision capture, and export affordances.
- [x] Added backend and frontend tests for scoring parity, identity fallback, persistence, decision separation, reviewed-only exports, queue rendering/filtering/selection, save flow, provenance disclosure, and export actions.
- [x] Documented console run commands in `README.md` and `.ai/COMMANDS.md`.

## Resolved earlier (2026-05-05 public review digest)

- [x] Added deterministic Markdown digest generation from `reports/gap_run_*.json` via `scripts/export_review_digest.py`.
- [x] Added public sample mode backed by `tests/fixtures/sample_gap_run.json`.
- [x] Added scoring/action/CLI tests for coverage score, security score, reviewer action labels, top-level tables, `--top-n`, summary counts, deterministic timestamp behavior, sample mode, and de-duped candidate briefs.
- [x] Generated `reports/discovery_digest_20260505.md` from the real 2026-05-05 GHSA report.
- [x] Documented digest usage in public-facing README files and local commands.

## Resolved this session (2026-05-03 PM cleanup)

- [x] Renamed GitHub repo `persistent-agent-security` → `aidefend-discovery`; updated local `origin` URL.
- [x] Consolidated loose `~/Desktop/repos/notes - aidefend discovery` into `docs/aidefend_discovery/NOTES.md`.
- [x] Consolidated loose `~/Desktop/repos/explanation of discovery.md` into `docs/aidefend_discovery/TECHNICAL_OVERVIEW.md`.
- [x] Purged stale `persistent-agent-security` references from active files (User-Agents, `gh` examples, `.ai/OPEN_LOOPS.md`, `.ai/CURRENT.md`).
- [x] Audited `docs/aidefend_discovery/ROADMAP.md` and `README.md` against current state; flipped Phase 1/2/3/4 checkboxes that had shipped, annotated embeddings re-open trigger, marked taxonomy-drift deferral resolved.
- [x] Updated `agent-continuity` global routing to the renamed GitHub repo.

## Resolved earlier (2026-05-03 architecture build-out)

- [x] Block A: Phase 1 hygiene + NVD auth (commit `4632242`).
- [x] Block C: sqlite candidate store + idempotency + export (commit `82a0972`).
- [x] Block G: GHSA connector (commit `09ed4e8`).
- [x] Block B: CWE→tactic bridge + taxonomy anchor diff (commit `dc2db82`).
- [x] Block I: 25-row gold corpus + eval upgrade (commit `d9e6b11`).
- [x] Block F: MCP discovery tools bundled under `services/aidefend-mcp/`.
- [x] Blocks E + H: governance templates + nightly scheduler workflow + secret provisioning.

## Resolved earlier (pre-2026-05-03)

- [x] Initialize safe repo-local `.ai` scaffold.
- [x] Phase 2A NVD connector baseline (anonymous mode + sqlite cursor) integrated into discovery pipeline.
- [x] Rename working identity to AIDEFEND Discovery in repo docs.
- [x] Author [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md); harden Phase 1 exit to require merged upstream PR; add ROADMAP "Deferred with reasoning" section with re-open triggers.
- [x] Fix stale `persistent-agent-security-discovery/*` User-Agent strings in `rss_ingest.py` / `nvd_ingest.py`.
