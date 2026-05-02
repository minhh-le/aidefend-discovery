# Context Index

Updated: 2026-05-02 (session closeout: HANDOFF/CURRENT/OPEN_LOOPS/DECISIONS aligned)

## Purpose

Repo-local continuity packet for Persistent Agent Security.

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

- `scripts/` — security automation scripts (includes `aidefend_discovery/` + `run_discovery_gap.py`).
- `docs/aidefend_discovery/` — **roadmap** (`ROADMAP.md`), **discoveries/** (dated research syntheses), review contract, maintainer alignment for AIDEFEND + discovery R&D.
- `lab/` — local lab configs; **AIDEFEND discovery** lives under `lab/aidefend_discovery/` (allowlist + README).
- `detections/` — detection logic/rules.
- `reports/` — deliverable/report drafts.
- `findings/` — finding writeups.
- `evidence-redacted/` — sanitized evidence only.
- `tests/` — tests for scripts/detections.
- `docs/` — supporting documentation.
