# AIDEFEND Discovery technical overview

**AIDEFEND discovery** is the **observation and correlation layer** that sits beside the curated AIDEFEND corpus: it ingests **public, allowlisted or API-backed signals**, normalizes them into **typed candidates** with citations, scores them against the **approved baseline**, and emits **gap reports** plus SQLite-backed history for review—without ever writing canonical framework data.

This document describes the subsystem implemented under [`lab/aidefend_discovery/`](../../lab/aidefend_discovery/) and [`scripts/aidefend_discovery/`](../../scripts/aidefend_discovery/).

---

## Relationship to [aidefense-framework](https://github.com/edward-playground/aidefense-framework)

| Layer | Role |
|-------|------|
| **Structured (framework)** | Authoritative defenses: tactic modules in `tactics/*.js`, generated [`data/data.json`](https://github.com/edward-playground/aidefense-framework/blob/main/data/data.json), site ([aidefend.net](https://aidefend.net)), threat mappings to OWASP / MAESTRO / MITRE ATLAS / NIST AML / SAIF / DASF / Cisco, etc. |
| **Discovery (this repo)** | **Read-only** consumption of `data.json` to flatten `AID-*` techniques (names, descriptions, keywords, `defendsAgainst`, pillars, phases). Candidates and gaps are **hypotheses**; promotion is **manual**: edit `tactics/*.js`, run `node scripts/generate-dataset.js` upstream. See [`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md). |

Nothing in discovery auto-mutates `data.json`. Maintainer alignment: [`MAINTAINER_ALIGNMENT.md`](MAINTAINER_ALIGNMENT.md).

---

## Relationship to [aidefend-mcp](https://github.com/edward-playground/aidefend-mcp)

[aidefend-mcp](https://github.com/edward-playground/aidefend-mcp) indexes the **approved** framework for semantic search (REST + MCP). Discovery extends that stack with an **optional, strictly labeled** namespace so assistants never confuse candidates with official `AID-*` facts:

- Tools such as **`search_discovery_candidates`** and **`explain_candidate_mapping`** operate on a **local discovery store** (SQLite schema produced by this pipeline; configured via e.g. `DISCOVERY_DB_PATH` in MCP settings).
- Responses carry an explicit **discovery namespace / disclaimer**; official technique IDs appear only in documented sidecars when bridging candidates to the corpus.

Implement details and contracts live in aidefend-mcp (`app/tools/*`, tests under `tests/test_discovery_tools.py`). Operational coupling: run ingestion here → expose the resulting DB path to MCP.

---

## What the pipeline does (end-to-end)

1. **Ingest** — Connectors pull normalized items:
   - **RSS/Atom** (`rss_ingest.py`): feed URL must match [`feeds.allowlist`](../../lab/aidefend_discovery/feeds.allowlist); optional **Trafilatura** page fetch for hosts in [`page_fetch.allowlist`](../../lab/aidefend_discovery/page_fetch.allowlist).
   - **NVD** (`nvd_ingest.py`): CVE 2.0 API, cursor/window state, optional `NVD_API_KEY`.
   - **GHSA** (`ghsa_ingest.py`): GitHub Security Advisory API; PAT recommended (`GH_PAT_FOR_GHSA` / `GITHUB_TOKEN`).

2. **Normalize** — Each item becomes a **`CandidateFinding`** ([`schemas.py`](../../scripts/aidefend_discovery/schemas.py)): stable `id`, `status`, title/summary, `source_urls`, `retrieved_at`, hashes, optional extracted **`entities`** (CVEs, CWEs, packages, versions), and retrieval-oriented fields (`body_retrieval`, chunk queries, etc.).

3. **Baseline** — [`baseline.py`](../../scripts/aidefend_discovery/baseline.py) loads `data.json`, flattens techniques into searchable **`TechniqueRecord`** rows and derives heuristic **threat-ID tokens** for overlap checks against `defendsAgainst` text.

4. **Gap detection** — [`bm25_index.py`](../../scripts/aidefend_discovery/bm25_index.py) ranks baseline techniques against candidate text; [`run_discovery_gap.py`](../../scripts/run_discovery_gap.py) builds **`GapReport`** rows: top-k `AID-*` neighbors, BM25 scores, `threat_id_overlap`, `is_gap` / `gap_reason`, suggested tactics/pillars/phases, lexical overlap terms for explainability.

5. **Deterministic bridges** — [`bridge.py`](../../scripts/aidefend_discovery/bridge.py) merges **YAML CWE → tactic/pillar/phase hints** ([`bridges/cwe_to_tactic.yaml`](../../lab/aidefend_discovery/bridges/cwe_to_tactic.yaml)) into gap output as **additive, cited** rationales (never replacing BM25).

6. **Persistence** — [`state_store.py`](../../scripts/aidefend_discovery/state_store.py): SQLite run ledger, candidate upserts, connector cursors (`connector_state.*`). Append-only **`candidates.jsonl`** and dated **`reports/gap_run_*.json`** bundles remain the human-review artifacts.

7. **Taxonomy regression** — **`anchor_diff.py`** (see [`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md)) diffs vendored upstream anchor snapshots under [`taxonomy_anchors/`](../../lab/aidefend_discovery/taxonomy_anchors/) against framework mappings so promotions do not fork vocabulary from OWASP / NIST / MAESTRO / etc.

---

## Operator entry points

- **Runbook & CLI examples:** [`lab/aidefend_discovery/README.md`](../../lab/aidefend_discovery/README.md)
- **Review vocabulary & promotion:** [`REVIEW_CONTRACT.md`](REVIEW_CONTRACT.md), [`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md)
- **Architecture notes & metrics framing:** [`NOTES.md`](NOTES.md)
- **Phased evolution:** [`ROADMAP.md`](ROADMAP.md)
- **Research log:** [`discoveries/INDEX.md`](discoveries/INDEX.md)

---

## Design constraints (summary)

- **Dual namespace:** Candidates ≠ approved `AID-*` rows in UX, APIs, and MCP.
- **Evidence:** Citations, hashes, and optional license notes are first-class; ingestion respects allowlists and third-party terms.
- **Human gate:** Accept/reject/promote with typed rejection reasons ([`schemas.REJECTION_REASONS`](../../scripts/aidefend_discovery/schemas.py)); no silent merge into the framework.
