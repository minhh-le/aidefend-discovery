# Handoff

Updated: 2026-05-02 (architecture-edit session: promotion playbook + Phase 1 exit hardening + UA fix)
Updated by: Claude Code
Verification: `.venv/bin/python -m unittest discover -s tests -v` (22 tests, all pass); from `../agent-continuity`: `python3 scripts/validate_continuity.py`, `python3 scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery`.

## Current Goal

Close Phase 1 by merging the first upstream promotion PR (using [`PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md)), and continue **Phase 2** work: taxonomy-anchor diff (prerequisite for resuming routine promotions), GHSA connector, CVE↔GHSA enrichment joins, optional API auth paths, ranking/filtering improvements.

## Last Meaningful Work

- **Promotion playbook authored:** [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) — pre-flight checks, Shape A (extend `defendsAgainst`) vs Shape B (new technique), tactic-letter table, `CandidateFinding`→technique crosswalk with explicit schema-gap callouts (`toolsOpenSource`/`toolsCommercial`/`implementationGuidance` are reviewer-authored at promotion time), PR description template, smoke-test step. Includes a **soft rule** pausing upstream promotions until the Phase 2 taxonomy-anchor diff lands.
- **Phase 1 exit hardened** in [`docs/aidefend_discovery/ROADMAP.md`](../docs/aidefend_discovery/ROADMAP.md): now requires a merged upstream promotion PR, not just a renderable demo story. Loop must close end-to-end.
- **Deferred-with-reasoning section added** to ROADMAP listing six items consciously held with explicit re-open triggers (is_gap two-trigger noise, BM25 vuln-shape mismatch, license-posture honor system, taxonomy drift, BM25 field weighting, body cap/chunk budget).
- **Stale-state fix:** HTTP User-Agent strings in `scripts/aidefend_discovery/rss_ingest.py` and `nvd_ingest.py` updated from `persistent-agent-security-discovery/*` placeholder URLs to `aidefend-discovery/*` with the actual `minhh-le/persistent-agent-security` remote URL.
- **Decisions log:** [`.ai/DECISIONS.md`](DECISIONS.md) entry recording the playbook authorship, hardened exit, deferral decisions, and the soft rule.

## Next Recommended Action

- **Promotion shake-out:** pick one credible candidate from `reports/gap_run_*.json` (or run NVD connector to produce a fresh one), walk it through `PROMOTION_PLAYBOOK.md` Shape A path, and open the upstream PR. This is the Phase 1 exit bar and will surface any schema gaps cheaply.
- **Phase 2 taxonomy-anchor diff:** prerequisite for resuming routine promotions — this is the architectural fix for vocabulary drift; everything else in Phase 2 (GHSA, embeddings rerank, CWE→tactic bridge) is downstream of it.
- **Phase 2B GHSA connector:** `GET /advisories` list/detail with cursor + PAT, CVE↔GHSA enrichment joins, AI-relevance filters.
- Add optional NVD auth mode (`NVD_API_KEY`) and stronger retry/backoff policy tuning.

## Known Pitfalls

- Do not store secrets or raw sensitive evidence.
- Do not infer targets or scope.
- Do not run security tooling against third-party systems without explicit authorization.
- Do not treat discovery candidates as approved `AID-*` techniques without upstream merge.
