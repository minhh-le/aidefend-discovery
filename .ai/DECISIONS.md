# Decisions

Updated: 2026-05-05

## 2026-05-05 — Public review digest uses single-run JSON as v1 product surface

Decision: Add a deterministic Markdown digest generator over `reports/gap_run_*.json`
as the public-review surface for discovery candidates. Keep sqlite backlog/history
out of v1, expose two numeric indicators (`Coverage Score`, `Security Score`),
use explicit reviewer action labels, and keep raw provenance in candidate brief
evidence/provenance sections instead of top-level tables.

Rationale: Single-run JSON is easiest for public testers to reproduce and reason
about without API keys or a local sqlite state store. The digest doubles as a
future UI product spec while preserving the backend candidate/gap data contract
and avoiding LLM-generated review text.

## 2026-04-30 — Start as safe empty scaffold

Decision: Initialize the repo with only continuity structure and safety policy, no project-specific content.

Rationale: Security work needs explicit scope and evidence handling rules before tooling, targets, or findings are added.

## 2026-05-01 — AIDEFEND discovery prototype alignment

Decision: Implement the “structured baseline + discovery” thin slice in this repo (read-only vs aidefense-framework), document review/MCP/taxonomy alignment in [docs/aidefend_discovery/MAINTAINER_ALIGNMENT.md](../docs/aidefend_discovery/MAINTAINER_ALIGNMENT.md), and defer founder confirmation only where noted there (e.g. CC BY redistribution nuance, public surface for candidates).

Rationale: Keeps the canonical KB in aidefense-framework while proving ingestion → BM25 gap scoring → human-review contract locally.

## 2026-05-02 — Phase 1 enrichment + API discover closeout

Decision: Ship Trafilatura-based page extract (host allowlist only), entity extraction, chunk max-pool BM25, lexical overlap explainability, and persist NVD/GitHub REST connector enumeration as dated discovery docs—not crawl4ai for now.

Rationale: Official APIs and static HTML extractors match maintainer alignment; crawl4ai deferred until JS-rendered sources dominate.

## 2026-05-02 — Phase 2A NVD-first delivery boundary

Decision: Implement NVD incremental ingestion first (anonymous mode), with explicit `--source nvd` dispatch, CVE/CWE normalization, and sqlite cursor persistence, while deferring GHSA ingestion and auth-enabled connector paths.

Rationale: Delivers a stable vertical slice with minimal moving parts, validates connector-state plumbing in production code, and preserves clear follow-up boundaries for GHSA, auth, and ranking improvements.

## 2026-05-03 — Full roadmap build-out (Blocks A→J)

Decision: Ship the remainder of the AIDEFEND Discovery roadmap end-to-end in one
session, gated on user-provided NVD API key, GitHub PAT, and access to the
companion `aidefend-mcp` repo. Eight per-theme commits cover:
authenticated NVD ingest with retry/backoff, version-range entity regex,
feed audit script, sqlite candidate/run/gap-report store with idempotency
on `content_hash`, review CSV + metrics emitters, GHSA connector mirroring
NVD pattern, CWE→tactic bridge with citation-backed seed table (26 CWEs),
taxonomy anchor diff with 9 vendored YAMLs, hand-labeled 25-row gold corpus
with precision/recall/F1 eval upgrade, MCP discovery tools with namespace
wall + 14 contract tests, governance templates + quarterly audit checklist,
nightly GitHub Actions workflow with secret provisioning.

Rationale: User authorized full scope ("max-level founder gate"); the roadmap's
phase ordering was honored (A→C→G→B→I→F→E+H→J) so each block could be smoke-
tested against live data before the next was layered. Bridge precedes embeddings
deliberately — gold-eval baseline (recall_is_gap=0.0) confirms the embeddings
re-open trigger now fires, but with measurable signal rather than guesswork.
The MCP tools are isolated behind `DISCOVERY_DB_PATH`; namespace wall enforced
via contract tests so the discovery layer cannot blur into AIDEFEND truth even
when both surfaces ship together.

Out-of-scope deliberately: pushing `aidefend-mcp` Block-F changes upstream
(third-party repo; user steers PR copy per memory); rotating credentials that
appeared in chat transcripts (user-side action).

## 2026-05-02 — Promotion playbook + Phase 1 exit hardening + deferred-with-reasoning

Decision: Author [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) as the concrete shape mapping `CandidateFinding` → upstream `tactics/*.js` edits; harden Phase 1's exit criterion in [`ROADMAP.md`](../docs/aidefend_discovery/ROADMAP.md#phase-1--interpretable-signal) to require a **merged upstream promotion PR**, not just a renderable demo story; codify a "Deferred with reasoning" section listing six items consciously held with explicit re-open triggers; record a soft rule pausing upstream promotions until the Phase 2 taxonomy-anchor diff lands.

Rationale: Without a concrete promotion shape doc, Phase 1's exit ("demo one credible candidate ↔ defenses *because…* story") is unprovable end-to-end — accepted candidates stall in the queue and we get no honest signal on whether `is_gap` produces things maintainers want. Writing the playbook also stress-tests `CandidateFinding` for promotion-time data sufficiency, surfacing schema gaps cheaply. The deferred list prevents future-us from relitigating already-decided architectural calls (BM25 vuln-shape mismatch, license posture, taxonomy drift, field weighting). The anchor-diff guardrail blocks vocabulary forking before it accumulates.

## 2026-05-02 — Rename working identity to AIDEFEND Discovery

Decision: Treat **AIDEFEND Discovery** as the user-facing project name and clean stale security-scaffold continuity docs around the actual discovery pipeline. Keep the local checkout/repo slug unchanged for now.

Rationale: The repo's useful work is now centered on AIDEFEND candidate discovery, public advisory ingestion, and gap-review tooling. The previous broad scaffold name and placeholder security-project loops no longer described current work.

## 2026-05-05 — Rename GitHub repository and consolidate loose discovery docs

Decision: Rename the GitHub repository from `minhh-le/persistent-agent-security` to `minhh-le/aidefend-discovery`, update local `origin`, and consolidate loose discovery notes from `~/Desktop/repos` into `docs/aidefend_discovery/NOTES.md` and `docs/aidefend_discovery/TECHNICAL_OVERVIEW.md`.

Rationale: The project identity has stabilized around AIDEFEND Discovery. Keeping the GitHub slug, local checkout, continuity routing, and docs aligned prevents agents from routing to the old security scaffold name and keeps architecture/provenance notes under version control with the implementation.
