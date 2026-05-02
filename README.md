# Persistent Agent Security

Scaffold for persistent, agent-assisted security engineering work.

This repo intentionally starts with no project details, targets, customer data, evidence, or findings. It exists to prove that the continuity scaffold can be replicated into a new serious project repo.

## Scope

Future work may include security engineering research, detections, lab automation, findings, reports, and agent-assisted workflows.

## Safety

Do not commit secrets, credentials, customer data, raw exploit targets, private logs, packet captures, malware samples, or sensitive evidence unless there is an explicit storage policy. Prefer redacted summaries and external evidence references.

## AIDEFEND discovery (R&D)

Prototype aligned with [aidefense-framework](https://github.com/edward-playground/aidefense-framework): allowlisted RSS/Atom → optional **Trafilatura** page extract → enriched candidates → BM25 (chunk max-pool) + overlap hints vs `data/data.json`. Python deps: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`. See [`docs/aidefend_discovery/ROADMAP.md`](docs/aidefend_discovery/ROADMAP.md), [`lab/aidefend_discovery/README.md`](lab/aidefend_discovery/README.md), and [`docs/aidefend_discovery/REVIEW_CONTRACT.md`](docs/aidefend_discovery/REVIEW_CONTRACT.md).

## Start Here

1. Read `AGENTS.md`.
2. Read `.ai/CONTEXT_INDEX.md`.
3. Read `.ai/HANDOFF.md`.
4. Read `.ai/CURRENT.md`.
5. Read `.ai/OPEN_LOOPS.md`.
