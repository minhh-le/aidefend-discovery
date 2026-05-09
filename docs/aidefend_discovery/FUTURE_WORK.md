# AIDEFEND Discovery future work

This captures good ideas intentionally left outside the public local-demo v1.

## Multi-run comparison

- Compare candidate queues across runs.
- Show which gaps are new, repeated, resolved, or downgraded.
- Add run-to-run source health and failure trend views.

## Source configuration

- Richer source profiles with per-source rate limits, license posture, and
  reviewer ownership.
- Safer custom RSS onboarding with validation, preview, and allowlist PR export.
- More explicit NVD/GHSA date-window controls in the UI.

## Ranking quality

- Embeddings over technique and `defendsAgainst` strings.
- Cross-encoder rerank on BM25 top-20.
- Scope classifier for AI/security relevance.
- Gold-corpus expansion beyond 50 hand-labeled rows with routine precision,
  recall, and reviewer-disagreement reporting.

## Promotion automation

- Action Packet diff previews tied to exact tactic file syntax.
- Anchor-diff pre-flight surfaced in the UI.
- Draft PR generation that still requires human review and never treats
  candidates as approved truth.
- Post-merge feedback loop that marks promoted candidates with PR URL and
  upstream commit SHA.

## Deployment beyond local clone-and-run

- Optional packaged desktop build or container image.
- Hosted demo mode with fixture-only data.
- Authenticated team mode with explicit storage and secret-handling policy.
- Public Labs surface after redistribution and license posture are approved.

## UI and product polish

- Keyboard-first queue triage.
- Better responsive table density for very large queues.
- Candidate dedupe and grouping across sources inside the broad source sweep.
- Inline source-error remediation tips.
- Accessibility audit with screen-reader pass and reduced-motion verification.
