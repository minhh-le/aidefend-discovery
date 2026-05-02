# Current State

Updated: 2026-05-02

## Repo Purpose

**AIDEFEND Discovery** is a research and tooling workspace for finding, normalizing, scoring, and reviewing candidate additions or mappings for the AIDEFEND knowledge base.

## Current Status

- The repo has moved past the original empty security scaffold; its working identity is now **AIDEFEND Discovery**.
- `scripts/run_discovery_gap.py` supports `--source rss|nvd`. NVD mode uses `scripts/aidefend_discovery/nvd_ingest.py` (CVE API query/pagination/normalization) and `scripts/aidefend_discovery/state_store.py` (sqlite cursor key `nvd_lastmod_end`).
- Existing enrichment/scoring remains: optional Trafilatura page fetch, candidate enrichment (`summary_raw`, `body_extracted`, chunks, entities), BM25 chunk max-pool, and lexical overlap explainability in gap reports.
- **Research index:** [`docs/aidefend_discovery/discoveries/`](../docs/aidefend_discovery/discoveries/) (web extraction guidance; **NVD + GitHub global advisory REST** connector enumeration).
- No offensive targets, customer data, credentials, raw evidence, or proprietary security findings are tracked.
- Global continuity index may still route here for cross-repo R&D.

## Facts vs Assumptions

Facts:
- Discovery output is **candidate-only** until promoted in upstream aidefense-framework `tactics/*.js`.
- Phase 2A NVD baseline is implemented in anonymous mode; auth and GHSA are follow-on work.
- The local checkout is now `aidefend-discovery`; the GitHub remote may still be `minhh-le/persistent-agent-security` until the remote repository is renamed.

Needs definition later:
- Whether to rename the GitHub repository after the docs/local identity stabilizes.
- Public surface decision for candidate output: labs, MCP-only, website, or another channel.
- Redistribution rules for third-party advisory summaries beyond cited metadata.
