# Decisions

Updated: 2026-05-02

## 2026-04-30 — Start as safe empty scaffold

Decision: Initialize Persistent Agent Security with only continuity structure and safety policy, no project-specific content.

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
