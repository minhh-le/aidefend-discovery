# Discovery Risk Model

Updated: 2026-05-02

This repo is not an active testing or exploitation workspace. Its current scope is AIDEFEND discovery: read-only ingestion of public sources, candidate generation, gap scoring, and human review support.

## Scope

- In scope: allowlisted RSS/Atom feeds, NVD CVE API responses, GitHub global security advisories, local candidate JSONL/report generation, and reviewer-facing docs.
- Out of scope: probing third-party systems, exploit validation, private advisories, customer data, malware samples, packet captures, and automatic writes to upstream AIDEFEND truth.

## Assets

- Source citations and normalized candidate records.
- Local sqlite connector cursors.
- Generated gap reports.
- API tokens supplied through environment variables for higher public API limits.
- Upstream AIDEFEND dataset used as read-only comparison input.

## Trust Boundaries

- Public feeds and advisory APIs are untrusted input.
- Extracted article text is untrusted and may be incomplete, misleading, adversarial, or license-restricted.
- Local generated artifacts are candidate-only and must not be presented as approved `AID-*` knowledge.
- Environment variables and shell history are outside repo storage and must not be copied into docs or fixtures.

## Main Risks

- **Secret leakage:** API keys or tokens accidentally committed in docs, fixtures, state databases, logs, or command examples.
- **Source poisoning:** Feed/advisory content may contain misleading text, prompt-injection-style instructions, malformed HTML, or adversarial keywords.
- **Overclaiming:** BM25 scores, entity overlap, EPSS, or CVE/GHSA links can suggest hypotheses; they do not prove AIDEFEND gaps.
- **Redistribution mistakes:** Verbatim advisory text or extracted article bodies may carry third-party terms that need review before public surfacing.
- **Rate-limit abuse:** Unauthenticated or poorly throttled connectors can exceed NVD/GitHub limits.

## Controls

- Keep canonical `AID-*` promotion manual and upstream-only.
- Use allowlists for network sources and page fetch hosts.
- Keep API keys in environment variables or external secret stores only.
- Prefer cited summaries and metadata over raw copied text.
- Preserve candidate labeling in reports, MCP ideas, and docs.
- Add explicit retry/backoff and cursor behavior before sustained connector runs.
