# AIDEFEND Discovery

> **Turn public AI security signals into reviewed, audit-ready defense intelligence — without ever touching your canonical knowledge base.**

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/65cbd61d-4c91-48a2-b545-77af15055eb5" />

AIDEFEND Discovery is a local review workbench for security practitioners. It continuously watches public sources (NVD, GitHub Security Advisories, curated RSS feeds), surfaces AI-threat candidates worth your attention, scores them against your existing [AIDEFEND](https://aidefend.net) defenses, and gives you a structured place to make — and record — your call.

Nothing auto-promotes. You decide. Every decision is traceable.

---

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/b24d6821-8dd8-4101-a347-b40aef1dc3d0" />

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/cd8cc305-09a1-4ca7-b9cc-ea65047fc3b7" />

---

## Why AIDEFEND Discovery?

The AI threat landscape moves faster than any single team can manually monitor. New CVEs, advisories, and attack research drop daily. Without a structured way to evaluate them against what you already defend, coverage gaps quietly accumulate.

AIDEFEND Discovery gives you a repeatable, human-gated pipeline:

- **Find** — pull from NVD, GHSA, and allowlisted RSS feeds automatically
- **Score** — rank candidates against your existing `AID-*` techniques using lexical search, CWE bridges, and threat-ID overlap
- **Review** — inspect evidence, citations, and provenance in a clean workbench UI
- **Decide** — accept, reject, merge, hold, or monitor — with a typed reason every time
- **Export** — ship maintainer-ready Action Packets, Markdown digests, and CSV reports

---

## Quick Start

**Prerequisites:** Python 3.10+, Node.js 20+, `make` (optional)

```bash
# Clone and launch — that's it
git clone <this-repo>
cd aidefend-discovery
make demo
```

The launcher handles everything: virtual environment, Python dependencies, frontend build, local API startup, and browser open. If auto-open isn't available, it prints the URL.

No API keys required to run the curated demo.

---

## Three Ways to Run Discovery

| Mode | What it does | Needs keys? |
|------|-------------|-------------|
| **Curated demo** | Real GHSA/NVD-backed samples, zero network calls | No |
| **Live advisory scan** | Live GHSA + NVD pull, anonymous or keyed | Optional |
| **Broad source sweep** | GHSA + NVD + allowlisted RSS pipeline | Optional |

To unlock higher API rate limits:

```bash
export NVD_API_KEY=your_key_here
export GH_PAT_FOR_GHSA=your_pat_here   # or GITHUB_TOKEN
make demo
```

---

## The Review Workbench

The UI is a mission-control surface for your discovery queue:

- **Pipeline view** — Signals → Candidates → Coverage → Gap → Action Packet
- **Quality gates** — Review-ready candidates surface first; noisy broad-sweep results stay hidden until you ask for them
- **Evidence on demand** — Every candidate shows its source URLs, content hash, BM25 similarity score, nearest `AID-*` neighbors, and gap reasoning
- **Reviewer decisions** — Accept, reject (with typed reason), hold for evidence, merge to existing, or monitor — all saved to a local SQLite DB
- **Optional AI summaries** — On-demand per candidate via any OpenAI-compatible provider; pasted keys and AI outputs are never written to disk

---

## Optional AI Summaries

AI is entirely optional. Deterministic summaries always work out of the box.

To enable AI-assisted summaries, set your provider credentials before launching:

```bash
export AI_SUMMARY_PROVIDER=openrouter
export AI_SUMMARY_BASE_URL=https://openrouter.ai/api/v1
export AI_SUMMARY_API_KEY=your_key
export AI_SUMMARY_MODEL=your_model
make demo
```

You can also paste a session-only key directly in the UI. Pasted keys, prompts, and AI outputs are never written to the database, logs, or exports.

---

## What You Get Out

| Export | Contents |
|--------|----------|
| **Action Packet** | Candidate ID, source URLs, content hash, nearest techniques, gap summary, reviewer notes, recommended promotion shape |
| **Markdown digest** | Human-readable summary of the current run |
| **CSV** | All candidates with reviewer fields, ready for spreadsheet review |
| **JSON bundle** | Full run with embedded review decisions for audit |

Approved changes to the AIDEFEND framework still require a manual edit to upstream `tactics/*.js` files — AIDEFEND Discovery is read-only with respect to canonical framework data. See the [Promotion Playbook](docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) for the full workflow.

---

## MCP / REST Integration

The bundled MCP/REST service (`services/aidefend-mcp/`) exposes discovery candidates to AI assistants through a strictly labeled namespace — so your assistant never confuses a candidate with an approved `AID-*` technique.

Available tools: `search_discovery_candidates`, `explain_candidate_mapping`.

```bash
cd services/aidefend-mcp
export DISCOVERY_DB_PATH=../../lab/aidefend_discovery/discovery_state.db
export DISCOVERY_REPORTS_PATH=../../reports
pytest tests/test_discovery_tools.py
```

---

## Local Data

All runtime artifacts stay inside your local clone — nothing phones home.

| Artifact | Location |
|----------|----------|
| Demo gap reports | `reports/demo/gap_run_*.json` |
| Candidate log | `lab/aidefend_discovery/candidates.jsonl` |
| Discovery state DB | `lab/aidefend_discovery/discovery_state.db` |
| Reviewer decisions DB | `lab/aidefend_discovery/review_console.db` |
| Built frontend | `review_console/dist/` |

---

## Further Reading

- [Demo Runbook](docs/aidefend_discovery/DEMO_RUNBOOK.md) — step-by-step walkthrough
- [Promotion Playbook](docs/aidefend_discovery/PROMOTION_PLAYBOOK.md) — how candidates become `AID-*` entries
- [Technical Overview](docs/aidefend_discovery/TECHNICAL_OVERVIEW.md) — pipeline internals
- [Review Contract](docs/aidefend_discovery/REVIEW_CONTRACT.md) — reviewer decision vocabulary
- [Roadmap](docs/aidefend_discovery/ROADMAP.md) — what's next

---

## Attribution

The MCP service is MIT licensed. AIDEFEND framework content is attributed to [`edward-playground/aidefense-framework`](https://github.com/edward-playground/aidefense-framework) under CC BY 4.0. Imported snapshots are tracked in [`vendor/SNAPSHOTS.md`](vendor/SNAPSHOTS.md).
