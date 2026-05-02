# AIDEFEND discovery lab

Prototype slice for **structured baseline + discovery**: ingest either an allowlisted RSS/Atom source or NVD CVE API source, append **CandidateFinding** rows to `candidates.jsonl` (gitignored by default), and write a dated **GapReport** bundle under `reports/`.

## Prerequisites

- Python 3.10+
- Path to a built [aidefense-framework](https://github.com/edward-playground/aidefense-framework) `data/data.json`

## Configure feeds (RSS mode)

Edit `feeds.allowlist`: newline-separated URLs; fetches are rejected unless the `--feed-url` argument matches a line exactly.

## Page fetch (Trafilatura)

Phase 1 follows each item’s `source_urls[0]` with an HTTP GET when `--fetch-pages` is on (default). Only **hostnames** listed in `page_fetch.allowlist` are fetched (one per line, e.g. `github.com`). Use `--no-fetch-pages` to keep feed-only text. Add hosts deliberately—**robots.txt and terms still apply**.

## Run (RSS mode)

From repo root:

```bash
python3 scripts/run_discovery_gap.py \
  --data-json /path/to/aidefense-framework/data/data.json \
  --feed-url https://github.com/langchain-ai/langchain/releases.atom \
  --allowlist lab/aidefend_discovery/feeds.allowlist \
  --max-items 15
```

Tune `--gap-bm25-max` if almost every item flags as a gap or none do.

## Run (NVD mode, anonymous-only in Phase 2A)

Phase 2A supports NVD ingestion without API key handling yet. Keep request volume low to respect NVD public limits.

### Explicit window run

```bash
python3 scripts/run_discovery_gap.py \
  --source nvd \
  --data-json /path/to/aidefense-framework/data/data.json \
  --state-db lab/aidefend_discovery/discovery_state.db \
  --nvd-lastmod-start 2026-04-01T00:00:00Z \
  --nvd-lastmod-end 2026-04-07T00:00:00Z \
  --nvd-results-per-page 200 \
  --nvd-max-pages 2 \
  --no-fetch-pages \
  --max-items 20
```

### Cursor-driven run

When `--nvd-lastmod-start` and `--nvd-lastmod-end` are omitted, the runner uses:
- `connector_state.nvd_lastmod_end` from `--state-db` as window start when present
- otherwise a default 7-day lookback
- current UTC time as window end

```bash
python3 scripts/run_discovery_gap.py \
  --source nvd \
  --data-json /path/to/aidefense-framework/data/data.json \
  --state-db lab/aidefend_discovery/discovery_state.db \
  --nvd-results-per-page 200 \
  --nvd-max-pages 1 \
  --no-fetch-pages \
  --max-items 20
```

## Outputs

| Artifact | Location |
|----------|----------|
| Candidate append-only log | `lab/aidefend_discovery/candidates.jsonl` |
| Run bundle (candidates + gap_reports + params) | `reports/gap_run_YYYYMMDD.json` |
| Connector cursor state (SQLite) | `lab/aidefend_discovery/discovery_state.db` |

Long-term plan: [docs/aidefend_discovery/ROADMAP.md](../docs/aidefend_discovery/ROADMAP.md) (per-phase checklists). Research index: [docs/aidefend_discovery/discoveries/INDEX.md](../docs/aidefend_discovery/discoveries/INDEX.md). Review workflow: [docs/aidefend_discovery/REVIEW_CONTRACT.md](../docs/aidefend_discovery/REVIEW_CONTRACT.md).
