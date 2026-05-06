# AIDEFEND Discovery

A private monorepo workspace for AIDEFEND discovery: ingesting public signals,
producing candidate findings, reviewing them locally, serving AIDEFEND through
MCP/REST, and comparing against a tracked framework snapshot.

The repo is read-only with respect to canonical AIDEFEND truth. It produces
candidate records, gap reports, and review support; approved `AID-*` changes
still happen as explicit edits to framework tactic files, now vendored under
[`vendor/aidefense-framework/`](vendor/aidefense-framework/).

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
- full MCP/REST service under [`services/aidefend-mcp/`](services/aidefend-mcp/) with read-only discovery namespace tools, walled from official `AID-*` tools;
- tracked framework data/site snapshot under [`vendor/aidefense-framework/`](vendor/aidefense-framework/).

Open work is **precision tuning** (embeddings + cross-encoder rerank — re-open trigger fired on the 25-row gold corpus) and **operationalisation** (first upstream promotion PR per [`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](docs/aidefend_discovery/PROMOTION_PLAYBOOK.md), and running the nightly workflow for a few cycles).

## Safety

Do not commit secrets, credentials, customer data, raw exploit targets, private logs, packet captures, malware samples, or sensitive evidence. API keys belong in environment variables or external secret stores only. Public API data is still treated as untrusted input and candidate-only until reviewed.

## AIDEFEND discovery (R&D)

Prototype aligned with [aidefense-framework](https://github.com/edward-playground/aidefense-framework): allowlisted RSS/Atom, NVD, or GHSA input → optional **Trafilatura** page extract → enriched candidates → BM25 (chunk max-pool) + bridge/overlap hints vs bundled `vendor/aidefense-framework/data/data.json` → sqlite-backed review exports and metrics. Python deps: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. See [`docs/aidefend_discovery/MONOREPO.md`](docs/aidefend_discovery/MONOREPO.md), [`docs/aidefend_discovery/TECHNICAL_OVERVIEW.md`](docs/aidefend_discovery/TECHNICAL_OVERVIEW.md), [`docs/aidefend_discovery/ROADMAP.md`](docs/aidefend_discovery/ROADMAP.md), [`lab/aidefend_discovery/README.md`](lab/aidefend_discovery/README.md), and [`docs/aidefend_discovery/REVIEW_CONTRACT.md`](docs/aidefend_discovery/REVIEW_CONTRACT.md).

Run a no-network sample/replay path against the bundled framework data:

```bash
PYTHONPATH=scripts python3 scripts/run_discovery_gap.py \
  --source rss \
  --feed-url https://github.com/langchain-ai/langchain/releases.atom \
  --allowlist lab/aidefend_discovery/feeds.allowlist \
  --no-fetch-pages \
  --max-items 0 \
  --dry-run
```

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

## Local review console

The Public Demo Console reviews one `reports/gap_run_*.json` at a time with sqlite-backed reviewer decisions. Build the React UI once, then run the local Python API:

```bash
cd review_console
npm install
npm run build
cd ..
PYTHONPATH=scripts python3 -m aidefend_discovery.review_console \
  --report reports/gap_run_20260505.json \
  --db lab/aidefend_discovery/review_console.db \
  --port 8765
```

Open `http://127.0.0.1:8765`. Decisions are stored candidate-locally in sqlite, preserving backend `recommended_action` separately from reviewer `review_decision`. Reviewed-only Markdown and CSV exports are available from the console toolbar.

For frontend development, run the API above and in another shell:

```bash
cd review_console
npm run dev
```

## MCP / REST service

The full AIDEFEND MCP/REST service is vendored at
[`services/aidefend-mcp/`](services/aidefend-mcp/) from
`minhh-le/aidefend-mcp@118c56c`. It defaults to the bundled framework snapshot
for local sync. To expose discovery candidate tools, point it at a local
runtime sqlite DB and reports directory:

```bash
cd services/aidefend-mcp
export DISCOVERY_DB_PATH=../../lab/aidefend_discovery/discovery_state.db
export DISCOVERY_REPORTS_PATH=../../reports
pytest tests/test_discovery_tools.py
```

When `DISCOVERY_DB_PATH` is unset, discovery tools return a graceful
"not configured" response. When configured, every discovery response carries
`discovery_namespace: true` and a disclaimer.

## Attribution

Imported snapshots are tracked in [`vendor/SNAPSHOTS.md`](vendor/SNAPSHOTS.md).
The MCP service is MIT licensed. The AIDEFEND framework content is attributed to
`edward-playground/aidefense-framework` and published under CC BY 4.0 upstream.
This discovery consolidation repo stays private for now.

## Start Here

1. Read `AGENTS.md`.
2. Read `.ai/CONTEXT_INDEX.md`.
3. Read `.ai/HANDOFF.md`.
4. Read `.ai/CURRENT.md`.
5. Read `.ai/OPEN_LOOPS.md`.
