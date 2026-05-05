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

## Feed allowlist hygiene

Audit feed reachability before a run; emits `reports/feed_audit_YYYYMMDD.json`:

```bash
python3 scripts/audit_feeds.py --allowlist lab/aidefend_discovery/feeds.allowlist
```

Exit code: `0` if ≥1 feed reachable, `1` if all dead. Pin one stable feed in CI as the smoke-test target — currently **LangChain releases atom** (the longest-lived in the allowlist).

## Run (NVD mode)

NVD authenticated mode is now supported. Set `NVD_API_KEY` in env to lift the rate limit from 5 req/30s (anonymous) to 50 req/30s. Without the key, the connector still works at the lower limit. Retries on 403/429/5xx use exponential backoff with jitter; capped at 5 attempts; honors `Retry-After`.

### Explicit window run (authenticated)

```bash
NVD_API_KEY=$NVD_API_KEY \
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

## Run (GHSA mode)

GitHub Security Advisory ingestion. Set `GH_PAT_FOR_GHSA` in env (preferred) or
`GITHUB_TOKEN` (fallback). Anonymous calls hit the 60 req/hr unauthenticated
limit and are not recommended.

```bash
GH_PAT_FOR_GHSA=$GH_PAT \
python3 scripts/run_discovery_gap.py \
  --source ghsa \
  --data-json /path/to/aidefense-framework/data/data.json \
  --state-db lab/aidefend_discovery/discovery_state.db \
  --ghsa-updated-after 2026-04-01T00:00:00Z \
  --ghsa-per-page 100 \
  --ghsa-max-pages 3 \
  --ghsa-severity high \
  --no-fetch-pages \
  --max-items 50
```

Cursor-driven (no `--ghsa-updated-after`): the runner reads
`connector_state.ghsa_updated_after` from the state DB, ingests forward, and
advances the cursor to the most recent `retrieved_at` after a successful run.

GHSA candidates carry `entities.cves`, `entities.cwes`, `entities.version_constraints`
(`vulnerable:<range>` and `patched:<version>`), `ghsa_packages` (ecosystem:name),
and `ghsa_severity`.

### Cursor-driven run (NVD)

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

## Scheduled run (CI)

`.github/workflows/discovery-nightly.yml` runs the full pipeline every day at
09:00 UTC and opens an auto-PR with the new dated reports. Manual trigger:

```bash
gh workflow run discovery-nightly.yml --repo minhh-le/aidefend-discovery
gh run watch --repo minhh-le/aidefend-discovery
```

Required repo secrets (provision once):
```bash
printf "%s" "$NVD_API_KEY"     | gh secret set NVD_API_KEY     --repo minhh-le/aidefend-discovery
printf "%s" "$GH_PAT_FOR_GHSA" | gh secret set GH_PAT_FOR_GHSA --repo minhh-le/aidefend-discovery
```

The workflow opens but never auto-merges PRs — preserves the discovery layer's
"no silent overwrites" principle. Reviewer follows
[`PROMOTION_PLAYBOOK.md`](../docs/aidefend_discovery/PROMOTION_PLAYBOOK.md).

## Outputs

| Artifact | Location |
|----------|----------|
| Candidate append-only log | `lab/aidefend_discovery/candidates.jsonl` |
| Run bundle (candidates + gap_reports + params) | `reports/gap_run_YYYYMMDD.json` |
| Connector cursor state (SQLite) | `lab/aidefend_discovery/discovery_state.db` |

Long-term plan: [docs/aidefend_discovery/ROADMAP.md](../docs/aidefend_discovery/ROADMAP.md) (per-phase checklists). Research index: [docs/aidefend_discovery/discoveries/INDEX.md](../docs/aidefend_discovery/discoveries/INDEX.md). Review workflow: [docs/aidefend_discovery/REVIEW_CONTRACT.md](../docs/aidefend_discovery/REVIEW_CONTRACT.md).
