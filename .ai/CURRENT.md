# Current State

Updated: 2026-05-02

## Repo Purpose

Persistent Agent Security is a scaffold for future agent-assisted security engineering work.

## Current Status

- Initialized as an empty/safe scaffold.
- **AIDEFEND discovery lab:** `scripts/run_discovery_gap.py` now supports `--source rss|nvd`. NVD mode uses `scripts/aidefend_discovery/nvd_ingest.py` (CVE API query/pagination/normalization) and `scripts/aidefend_discovery/state_store.py` (sqlite cursor key `nvd_lastmod_end`).
- Existing enrichment/scoring remains: optional Trafilatura page fetch, candidate enrichment (`summary_raw`, `body_extracted`, chunks, entities), BM25 chunk max-pool, and lexical overlap explainability in gap reports.
- **Research index:** [`docs/aidefend_discovery/discoveries/`](../docs/aidefend_discovery/discoveries/) (web extraction guidance; **NVD + GitHub global advisory REST** connector enumeration).
- No offensive targets, customer data, credentials, raw evidence, or proprietary security findings are tracked by default.
- Global continuity index may still route here for cross-repo R&D.

## Facts vs Assumptions

Facts:
- This repo is intended to prove the `.ai` continuity scaffold can be replicated to a new project.
- Discovery output is **candidate-only** until promoted in upstream aidefense-framework `tactics/*.js`.
- Phase 2A NVD baseline is implemented in anonymous mode; auth and GHSA are follow-on work.

Needs definition later:
- First dedicated defensive/offensive security line of effort beyond AIDEFEND R&D.
- Scope/authorization boundaries for any active testing.
- Evidence storage policy for non–AIDEFEND work.
