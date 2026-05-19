# Agent Instructions: AIDEFEND Discovery

## Repo-local continuity temporarily disabled

The repo-local `.ai` continuity packet is disabled for now at the user's request.

- Do **not** automatically read `.ai/CONTEXT_INDEX.md`, `.ai/CURRENT.md`, `.ai/HANDOFF.md`, `.ai/OPEN_LOOPS.md`, `.ai/DECISIONS.md`, or `.ai/COMMANDS.md` as prerequisite startup context.
- Do **not** automatically update `.ai/HANDOFF.md`, `.ai/CURRENT.md`, `.ai/OPEN_LOOPS.md`, `.ai/DECISIONS.md`, or `.ai/SESSION_LOG.md` during closeout.
- Treat existing `.ai/` content as parked archival state. Preserve it; do not delete or rewrite it during normal work.
- For ordinary work in this repo, follow only the user's current prompt and normal project files/docs.

Security rules still apply:

- Never commit secrets, credentials, private keys, tokens, cookies, customer data, raw sensitive logs, malware samples, packet captures, or exploit target details unless the user explicitly approves a storage policy.
- Prefer public API metadata, redacted notes, and external source references over storing raw sensitive evidence.
- Keep candidate records factual and distinguish confirmed evidence from hypotheses.
- If a task could affect third-party systems, pause and get explicit scope/authorization.
- Run `git status --short --branch` before summarizing changed files when modifying the repo.
