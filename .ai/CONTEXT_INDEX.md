# Context Index

Updated: 2026-05-02 (promotion playbook + Phase 1 exit hardening + deferred-with-reasoning)

## Purpose

Repo-local continuity packet for **AIDEFEND Discovery**.

## Startup Order

1. `AGENTS.md`
2. `.ai/CURRENT.md`
3. `.ai/HANDOFF.md`
4. `.ai/OPEN_LOOPS.md`
5. `.ai/DECISIONS.md`
6. `.ai/COMMANDS.md`
7. `.ai/FINDINGS_INDEX.md`
8. `.ai/THREAT_MODEL.md`

## Main Areas

- `scripts/` — discovery automation scripts (`aidefend_discovery/` + `run_discovery_gap.py`).
- `docs/aidefend_discovery/` — **roadmap** (`ROADMAP.md`), **promotion playbook** (`PROMOTION_PLAYBOOK.md`), **quality audit checklist** (`QUALITY_AUDIT_CHECKLIST.md`), **discoveries/** (dated research syntheses), review contract, maintainer alignment for AIDEFEND + discovery R&D.
- `lab/aidefend_discovery/bridges/cwe_to_tactic.yaml` — 26-CWE bridge table (Block B).
- `lab/aidefend_discovery/taxonomy_anchors/` — 9 vendored framework anchor YAMLs (Block B).
- `lab/aidefend_discovery/gold/` — 25 hand-labeled rows + audit log (Block I).
- `.github/workflows/discovery-nightly.yml` — scheduled NVD+GHSA+RSS+anchor-diff pipeline (Block H).
- `lab/` — local lab configs; **AIDEFEND discovery** lives under `lab/aidefend_discovery/` (allowlist + README).
- `reports/` — generated gap report examples and deliverable drafts.
- `tests/` — tests for discovery scripts.
- `docs/` — supporting documentation.
