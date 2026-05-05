# AIDEFEND Discovery

A research and tooling workspace for AIDEFEND discovery: ingesting public signals, producing candidate findings, and comparing them against the upstream AIDEFEND knowledge base.

The repo is read-only with respect to the canonical AIDEFEND dataset. It produces candidate records, gap reports, and review support; approved `AID-*` truth still lives upstream in [`aidefense-framework`](https://github.com/edward-playground/aidefense-framework).

## Scope

Current scope is the AIDEFEND discovery pipeline:

- allowlisted RSS/Atom ingestion;
- optional Trafilatura page extraction;
- NVD CVE API ingestion (with `NVD_API_KEY` auth + retry/backoff) and GitHub Security Advisory ingestion (with `GH_PAT_FOR_GHSA` auth + cursor pagination);
- candidate enrichment with CVE/GHSA/CWE entities and retrieval chunks;
- BM25 gap scoring with CWE→tactic bridge rationales and reviewer-facing explainability;
- taxonomy anchor diff against 9 vendored upstream framework YAMLs (MITRE ATLAS, OWASP LLM/ML/Agentic, NIST AI 100-2, MAESTRO, SAIF, Databricks DASF, Cisco AITech);
- deterministic Markdown public review digests from single-run `gap_run_*.json` reports;
- sqlite candidate store with idempotency, CSV review export, and JSON metrics;
- nightly GitHub Actions workflow with auto-PR (never auto-merged);
- read-only MCP discovery tools in companion `aidefend-mcp` repo (namespace-walled from official `AID-*` tools).

Open work is **precision tuning** (embeddings + cross-encoder rerank — re-open trigger fired on the 25-row gold corpus) and **operationalisation** (first upstream promotion PR per [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](docs/aidefend_discovery/PROMOTION_PLAYBOOK.md), and running the nightly workflow for a few cycles).

## Safety

Do not commit secrets, credentials, customer data, raw exploit targets, private logs, packet captures, malware samples, or sensitive evidence. API keys belong in environment variables or external secret stores only. Public API data is still treated as untrusted input and candidate-only until reviewed.

## AIDEFEND discovery (R&D)

Prototype aligned with [aidefense-framework](https://github.com/edward-playground/aidefense-framework): allowlisted RSS/Atom, NVD, or GHSA input → optional **Trafilatura** page extract → enriched candidates → BM25 (chunk max-pool) + bridge/overlap hints vs `data/data.json` → sqlite-backed review exports and metrics. Python deps: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. See [`docs/aidefend_discovery/TECHNICAL_OVERVIEW.md`](docs/aidefend_discovery/TECHNICAL_OVERVIEW.md), [`docs/aidefend_discovery/ROADMAP.md`](docs/aidefend_discovery/ROADMAP.md), [`lab/aidefend_discovery/README.md`](lab/aidefend_discovery/README.md), and [`docs/aidefend_discovery/REVIEW_CONTRACT.md`](docs/aidefend_discovery/REVIEW_CONTRACT.md).

Generate a reviewer-facing Markdown digest from any single-run report:

```bash
python3 scripts/export_review_digest.py \
  --report reports/gap_run_20260505.json \
  --output reports/discovery_digest_20260505.md \
  --top-n 10
```

Public sample mode uses a checked-in fixture and does not require API keys:

```bash
python3 scripts/export_review_digest.py --sample --output reports/discovery_digest_sample.md
```

## Start Here

1. Read `AGENTS.md`.
2. Read `.ai/CONTEXT_INDEX.md`.
3. Read `.ai/HANDOFF.md`.
4. Read `.ai/CURRENT.md`.
5. Read `.ai/OPEN_LOOPS.md`.
