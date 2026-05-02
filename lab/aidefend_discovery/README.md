# AIDEFEND discovery lab

Prototype slice for **structured baseline + discovery**: ingest an allowlisted RSS/Atom URL, append **CandidateFinding** rows to `candidates.jsonl` (gitignored by default), and write a dated **GapReport** bundle under `reports/`.

## Prerequisites

- Python 3.10+
- Path to a built [aidefense-framework](https://github.com/edward-playground/aidefense-framework) `data/data.json`

## Configure feeds

Edit `feeds.allowlist`: newline-separated URLs; fetches are rejected unless the `--feed-url` argument matches a line exactly.

## Page fetch (Trafilatura)

Phase 1 follows each item’s `source_urls[0]` with an HTTP GET when `--fetch-pages` is on (default). Only **hostnames** listed in `page_fetch.allowlist` are fetched (one per line, e.g. `github.com`). Use `--no-fetch-pages` to keep feed-only text. Add hosts deliberately—**robots.txt and terms still apply**.

## Run

From repo root:

```bash
python3 scripts/run_discovery_gap.py \
  --data-json /path/to/aidefense-framework/data/data.json \
  --feed-url https://github.com/langchain-ai/langchain/releases.atom \
  --allowlist lab/aidefend_discovery/feeds.allowlist \
  --max-items 15
```

Tune `--gap-bm25-max` if almost every item flags as a gap or none do.

## Outputs

| Artifact | Location |
|----------|----------|
| Candidate append-only log | `lab/aidefend_discovery/candidates.jsonl` |
| Run bundle (candidates + gap_reports + params) | `reports/gap_run_YYYYMMDD.json` |

Long-term plan: [docs/aidefend_discovery/ROADMAP.md](../docs/aidefend_discovery/ROADMAP.md) (per-phase checklists). Research index: [docs/aidefend_discovery/discoveries/INDEX.md](../docs/aidefend_discovery/discoveries/INDEX.md). Review workflow: [docs/aidefend_discovery/REVIEW_CONTRACT.md](../docs/aidefend_discovery/REVIEW_CONTRACT.md).
