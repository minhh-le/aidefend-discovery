# Agent Instructions: Persistent Agent Security

This repo uses a repo-local `.ai` continuity packet.

Before work:

1. Read `.ai/CONTEXT_INDEX.md`.
2. Read `.ai/CURRENT.md`.
3. Read `.ai/HANDOFF.md`.
4. Read `.ai/OPEN_LOOPS.md`.
5. Read `.ai/DECISIONS.md`.
6. Read `.ai/COMMANDS.md`.
7. Run `git status --short --branch`.

Security rules:

- Never commit secrets, credentials, private keys, tokens, cookies, customer data, raw sensitive logs, malware samples, packet captures, or exploit target details unless the user explicitly approves a storage policy.
- Prefer `evidence-redacted/` plus external evidence references.
- Keep findings factual and distinguish confirmed evidence from hypotheses.
- If a task could affect third-party systems, pause and get explicit scope/authorization.

Closeout:

1. Update `.ai/HANDOFF.md`.
2. Update `.ai/CURRENT.md` if state changed.
3. Update `.ai/OPEN_LOOPS.md` if unresolved work changed.
4. Update `.ai/DECISIONS.md` for durable choices.
5. Append to `.ai/SESSION_LOG.md`.
6. Run relevant verification.
7. Commit and push coherent changes.
