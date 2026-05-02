# AIDEFEND Discovery

A research and tooling workspace for AIDEFEND discovery: ingesting public signals, producing candidate findings, and comparing them against the upstream AIDEFEND knowledge base.

The repo is read-only with respect to the canonical AIDEFEND dataset. It produces candidate records, gap reports, and review support; approved `AID-*` truth still lives upstream in [`aidefense-framework`](https://github.com/edward-playground/aidefense-framework).

## Scope

Current scope is the AIDEFEND discovery pipeline:

- allowlisted RSS/Atom ingestion;
- optional Trafilatura page extraction;
- NVD CVE API ingestion;
- candidate enrichment with CVE/GHSA/CWE entities and retrieval chunks;
- BM25 gap scoring and reviewer-facing explainability.

Phase 2 work is focused on GitHub global security advisories, CVE/GHSA enrichment joins, optional API auth paths, and better AI-relevance filtering.

## Safety

Do not commit secrets, credentials, customer data, raw exploit targets, private logs, packet captures, malware samples, or sensitive evidence. API keys belong in environment variables or external secret stores only. Public API data is still treated as untrusted input and candidate-only until reviewed.

## AIDEFEND discovery (R&D)

Prototype aligned with [aidefense-framework](https://github.com/edward-playground/aidefense-framework): allowlisted RSS/Atom or NVD API → optional **Trafilatura** page extract → enriched candidates → BM25 (chunk max-pool) + overlap hints vs `data/data.json`. Python deps: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. See [`docs/aidefend_discovery/ROADMAP.md`](docs/aidefend_discovery/ROADMAP.md), [`lab/aidefend_discovery/README.md`](lab/aidefend_discovery/README.md), and [`docs/aidefend_discovery/REVIEW_CONTRACT.md`](docs/aidefend_discovery/REVIEW_CONTRACT.md).

## Start Here

1. Read `AGENTS.md`.
2. Read `.ai/CONTEXT_INDEX.md`.
3. Read `.ai/HANDOFF.md`.
4. Read `.ai/CURRENT.md`.
5. Read `.ai/OPEN_LOOPS.md`.
