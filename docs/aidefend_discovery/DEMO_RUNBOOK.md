# AIDEFEND Discovery demo runbook

This runbook is for a public clone-and-run local demo.

## Prerequisites

- Python 3.10+
- Node.js 20+ and npm
- Optional: `make`

## One-command start

```bash
make demo
```

Or:

```bash
python3 scripts/run_demo.py
```

The launcher creates `.venv`, installs Python requirements, installs frontend
dependencies when needed, builds the React app, starts the local API, picks an
open port from `8765`, and opens the browser. Use `--no-open` when running on a
headless host.

## Optional keys

Live discovery works anonymously, but keys improve reliability:

```bash
export NVD_API_KEY=...
export GH_PAT_FOR_GHSA=...   # or GITHUB_TOKEN
```

Optional AI summary:

```bash
export AI_SUMMARY_PROVIDER=openrouter
export AI_SUMMARY_BASE_URL=https://openrouter.ai/api/v1
export AI_SUMMARY_API_KEY=...
export AI_SUMMARY_MODEL=...
```

The UI also accepts a session-only pasted AI key. The backend does not write
pasted keys, AI outputs, or prompt payloads to sqlite, JSON reports, logs, or
docs.

## Demo flow

1. Start with `Curated demo` to inspect real GHSA/NVD-backed sample evidence
   with deterministic review-ready briefs.
2. Review the source health strip. RSS should show allowlisted feeds. NVD and
   GHSA should show anonymous or key-configured status. AI should show enabled
   only when a model and key are configured.
3. Run `Live advisory scan` when you want current GHSA/NVD advisory evidence.
   If it returns fewer than 3 review-ready candidates, the UI recommends the
   curated demo rather than padding the queue with weak items.
4. Run `Broad source sweep` only when you want pipeline breadth, including
   allowlisted RSS. Release-note-like items stay outside the default queue.
5. Pick a candidate, inspect the readable sections, then expand evidence and
   raw provenance.
6. Save a reviewer decision: Promote, Merge Into Existing, Reject, Needs
   Evidence, or Monitor.
7. Export Markdown, CSV, JSON, or a selected-candidate Action Packet.

## AI payload policy

AI summaries are on demand and optional. The payload contains compact candidate
context only: title, source type/id, identifiers, short summary/excerpt,
severity, package/ecosystem, nearest AIDEFEND comparison, gap reason, bridge
rationales, and key source URLs. Full extracted article bodies are not sent by
default. Failures fall back to the deterministic summary.

## Local storage

| Artifact | Location |
| --- | --- |
| Demo reports | `reports/demo/gap_run_*.json` |
| Candidate append log | `lab/aidefend_discovery/candidates.jsonl` |
| Discovery state DB | `lab/aidefend_discovery/discovery_state.db` |
| Reviewer decisions DB | `lab/aidefend_discovery/review_console.db` |
| Built frontend | `review_console/dist/` |

## Troubleshooting

- If Node dependencies are missing, run `cd review_console && npm ci`.
- If the browser does not open, use the printed `http://127.0.0.1:<port>` URL.
- If NVD or GHSA rate-limits, add the optional key and restart the demo.
- If live RSS rejects a URL, add it to `lab/aidefend_discovery/feeds.allowlist`
  or use the advanced custom-feed escape hatch deliberately.
- If AI summary fails, the deterministic summary remains available and no
  review flow is blocked.
