<!--
Use this template when promoting a discovery candidate INTO the upstream
aidefense-framework repo as a tactics/*.js edit. See
docs/aidefend_discovery/PROMOTION_PLAYBOOK.md for the full playbook.

This PR is opened against `edward-playground/aidefense-framework`, NOT this
repo. Copy this template body into the PR description there.
-->

## Discovery promotion — <candidate title>

- **Discovery candidate:** `<candidate_id>` (`source_type=<rss|nvd_api|ghsa_api>`, `source_id=<...>`)
- **Source URLs:** <one bullet per source_urls entry from the candidate>
- **content_hash:** `<content_hash>`
- **GapReport summary:**
  - `nearest_technique_ids`: <top-5 from the gap report>
  - `max_bm25`: <value>
  - `gap_reason`: `<gap_reason>`
  - `bridge_rationales`: <flatten the relevant CWE→tactic rationale here>
- **Promotion shape:** A (extend `defendsAgainst`) | B (new technique)
- **Anchor-diff status:**
  - Latest anchor_diff report consulted: `reports/anchor_diff_YYYYMMDD.json`
  - Confirmed the upstream framework ID is NOT already mapped under different wording? Yes / No (and how)
- **kev_flag:** true | false

## Pre-flight checklist (from `PROMOTION_PLAYBOOK.md`)

- [ ] Candidate `status == "candidate"` and reviewer concurs with `gap_reason`.
- [ ] `license_note` is permissive OR PR uses only metadata + paraphrased description.
- [ ] Anchor-diff guardrail: ran `scripts/anchor_diff.py`, inspected `present_in_aidefend[]` for the relevant framework, confirmed no existing mapping matches the candidate.
- [ ] Citations resolve (every URL above 200-OK).
- [ ] No prior `promoted` row exists for this `content_hash`/`entities.cves`/`entities.ghsas`.

## Reviewer notes

<why this shape, why this pillar/phase, any framework-ID disambiguation, any
deferred follow-ups for the next promotion>

## Closes loop for

- discovery JSONL row id: `<candidate_id>`
- After merge: update `CandidateFinding.status` to `promoted` in the
  discovery JSONL with this PR's URL and the merged commit SHA.
