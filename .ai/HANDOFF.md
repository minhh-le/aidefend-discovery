# Handoff

Updated: 2026-05-02
Updated by: Cursor Agent
Verification: `.venv/bin/python -m pip install -r requirements.txt` then `PYTHONPATH=scripts .venv/bin/python -m unittest discover -s tests -v` (12 tests); `python3 scripts/validate_continuity.py` run from [`agent-continuity`](../../../agent-continuity) after global index/EFFORTS touch.

## Current Goal

Evolve **AIDEFEND-aligned discovery** from RSS-only toward **Phase 2 connectors** (NVD CVE 2.0 incremental + GitHub global advisories) while keeping canonical `AID-*` truth in aidefense-framework.

## Last Meaningful Work

- **Phase 1:** Trafilatura fetch behind [`lab/aidefend_discovery/page_fetch.allowlist`](../lab/aidefend_discovery/page_fetch.allowlist); chunked **max-pool BM25**; **CVE/GHSA/CWE** entities; **`nearest_lexical_overlap_terms`** on gap reports; [`requirements.txt`](../requirements.txt) + gold eval scaffold ([`scripts/eval_discovery_gold.py`](../scripts/eval_discovery_gold.py)).
- **Planning:** [`docs/aidefend_discovery/ROADMAP.md`](../docs/aidefend_discovery/ROADMAP.md) per-phase checklists; discover notes in [`docs/aidefend_discovery/discoveries/`](../docs/aidefend_discovery/discoveries/) including [NVD + GitHub API enumeration](../docs/aidefend_discovery/discoveries/2026-05-02-nvd-ghsa-connector-api.md).
- **Continuity:** Session started from **agent-continuity** validator + pickup via **AGENTS.md** / **CONTEXT_INDEX**; durable state remains in this repo’s `.ai/` packet.

## Next Recommended Action

- **This repo:** Implement **Phase 2** connectors per [NVD + GitHub API enumeration](../docs/aidefend_discovery/discoveries/2026-05-02-nvd-ghsa-connector-api.md) (NVD `lastMod*` windows + `apiKey`; GitHub `GET /advisories` with `ecosystem` + cursor + PAT); persist cursors in SQLite; grow [`lab/aidefend_discovery/gold/`](../lab/aidefend_discovery/gold/) labels.
- **Global index:** **agent-continuity** [`.ai/EFFORTS.md`](../../../agent-continuity/.ai/EFFORTS.md) effort `aidefend-discovery-mesh` mirrors routing for the same next step.

## Known Pitfalls

- Do not store secrets or raw sensitive evidence.
- Do not infer targets or scope.
- Do not run security tooling against third-party systems without explicit authorization.
- Do not treat discovery candidates as approved `AID-*` techniques without upstream merge.
