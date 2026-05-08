# AIDEFEND Discovery

AIDEFEND Discovery is a local product demo for turning public security signals
into reviewable AIDEFEND coverage intelligence: what happened, what defense
knowledge already exists, what may be missing, and what action a maintainer
should consider next.

The repo is read-only with respect to canonical AIDEFEND truth. It produces
candidate records, gap reports, reviewer decisions, and action packets.
Approved `AID-*` changes still require explicit human-reviewed edits to the
vendored framework tactic files under
[`vendor/aidefense-framework/`](vendor/aidefense-framework/).

## Quick Start

Prerequisites:

- Python 3.10+
- Node.js 20+ and npm
- Optional: `make`

Start the full local demo:

```bash
make demo
```

Equivalent direct command:

```bash
python3 scripts/run_demo.py
```

The launcher creates `.venv`, installs Python dependencies, installs frontend
dependencies when needed, builds the React console, starts the local Python API,
picks an open port from `8765`, and opens the browser. If browser auto-open is
not available, it prints the URL.

## What The Demo Does

The first screen is an operational mission-control surface:

- workflow: Signals -> Candidates -> Coverage -> Gap -> Action Packet
- first-run actions: run the checked-in sample, start an RSS quick scan,
  configure optional keys, and open the latest run
- source health: RSS allowlist, NVD anonymous/key status, GHSA anonymous/key
  status, optional AI summary status, and local data posture
- trust posture: candidates are not approved AIDEFEND truth, backend
  recommendations are separate from reviewer decisions, and data stays local
  unless a live source or AI summary is explicitly invoked

The review workbench lets you start discovery runs from the UI, watch progress
and errors, inspect candidates, expand evidence/provenance, save reviewer
decisions, request optional AI summaries, and export maintainer-ready artifacts.

## Discovery Presets

Available from the UI:

- `Quick Demo: sample report`, no network or API keys
- `RSS: AI framework releases`, allowlisted feeds
- `NVD: AI/ML keyword scan`, anonymous or `NVD_API_KEY`
- `GHSA: high-severity advisories`, anonymous or GitHub token
- `Full Sweep: RSS + NVD + GHSA`, one merged candidate queue

RSS uses [`lab/aidefend_discovery/feeds.allowlist`](lab/aidefend_discovery/feeds.allowlist)
by default. The UI includes an advanced custom-feed escape hatch, but the safe
default is allowlisted feeds only.

NVD and GHSA work without keys at public anonymous limits. Keys improve rate
limits and reliability:

```bash
export NVD_API_KEY=...
export GH_PAT_FOR_GHSA=...   # or GITHUB_TOKEN
make demo
```

## Optional AI Summaries

AI is not required. Deterministic summaries always work without an API key.

Configure AI with environment variables:

```bash
export AI_SUMMARY_PROVIDER=openrouter
export AI_SUMMARY_BASE_URL=https://openrouter.ai/api/v1
export AI_SUMMARY_API_KEY=...
export AI_SUMMARY_MODEL=...
make demo
```

You can also paste a session-only key in the UI. Pasted keys, prompt payloads,
and AI outputs are not written to sqlite, JSON reports, logs, or docs.

AI summaries are on demand per candidate. The backend sends compact structured
context only: title, source type/id, identifiers, short summary/excerpt,
severity, package/ecosystem, nearest AIDEFEND comparison, gap reason, bridge
rationales, and key source URLs. It does not send full raw extracted article
bodies by default. If AI is unavailable or fails, the UI shows the deterministic
summary instead.

## Exports

The export menu provides:

- Markdown digest for the current run
- CSV for all current candidates with reviewer fields
- JSON run bundle with review decisions
- Action Packet for the selected candidate

Action Packets follow
[`docs/aidefend_discovery/PROMOTION_PLAYBOOK.md`](docs/aidefend_discovery/PROMOTION_PLAYBOOK.md):
candidate id, source type/id, source URLs, content hash, nearest techniques,
gap summary, reviewer notes, recommended promotion shape, and optional
human-review-required draft tactic edit guidance.

## Local Data

Runtime artifacts stay in the clone:

| Artifact | Location |
| --- | --- |
| Demo reports | `reports/demo/gap_run_*.json` |
| Candidate append log | `lab/aidefend_discovery/candidates.jsonl` |
| Discovery cursor/state DB | `lab/aidefend_discovery/discovery_state.db` |
| Reviewer decisions DB | `lab/aidefend_discovery/review_console.db` |
| Built frontend | `review_console/dist/` |

These generated runtime files are local working artifacts. API keys belong in
environment variables or the UI session field only.

## Manual Development

Backend and built frontend:

```bash
cd review_console
npm ci
npm run build
cd ..
PYTHONPATH=scripts python3 -m aidefend_discovery.review_console \
  --report tests/fixtures/sample_gap_run.json \
  --db lab/aidefend_discovery/review_console.db \
  --port 8765
```

Frontend dev server:

```bash
cd review_console
npm run dev
```

Python tests:

```bash
PYTHONPATH=scripts python3 -m unittest discover -s tests -v
```

Frontend checks:

```bash
cd review_console
npm test
npm run build
```

## Pipeline CLI

The UI wraps the same local pipeline primitives. You can still run them from
the terminal:

```bash
python3 scripts/run_discovery_gap.py \
  --source rss \
  --feed-url https://github.com/langchain-ai/langchain/releases.atom \
  --allowlist lab/aidefend_discovery/feeds.allowlist \
  --no-fetch-pages \
  --max-items 15
```

Generate a deterministic digest from a report:

```bash
python3 scripts/export_review_digest.py --sample --output reports/discovery_digest_sample.md
```

## MCP / REST Service

The full AIDEFEND MCP/REST service is vendored at
[`services/aidefend-mcp/`](services/aidefend-mcp/). To expose discovery
candidate tools locally:

```bash
cd services/aidefend-mcp
export DISCOVERY_DB_PATH=../../lab/aidefend_discovery/discovery_state.db
export DISCOVERY_REPORTS_PATH=../../reports
pytest tests/test_discovery_tools.py
```

When `DISCOVERY_DB_PATH` is unset, discovery tools return a graceful
"not configured" response. Discovery responses carry `discovery_namespace:
true` and a disclaimer.

## More Docs

- [Demo runbook](docs/aidefend_discovery/DEMO_RUNBOOK.md)
- [Promotion playbook](docs/aidefend_discovery/PROMOTION_PLAYBOOK.md)
- [Future work](docs/aidefend_discovery/FUTURE_WORK.md)
- [Technical overview](docs/aidefend_discovery/TECHNICAL_OVERVIEW.md)
- [Roadmap](docs/aidefend_discovery/ROADMAP.md)
- [Review contract](docs/aidefend_discovery/REVIEW_CONTRACT.md)

## Attribution

Imported snapshots are tracked in [`vendor/SNAPSHOTS.md`](vendor/SNAPSHOTS.md).
The MCP service is MIT licensed. The AIDEFEND framework content is attributed
to `edward-playground/aidefense-framework` and published under CC BY 4.0
upstream.
