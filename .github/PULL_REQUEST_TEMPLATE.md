<!--
Generic PR template. For upstream promotion PRs (candidate → tactics/*.js
in aidefense-framework), use .github/PULL_REQUEST_TEMPLATE/discovery_promotion.md
instead — append `?template=discovery_promotion.md` to the PR URL or pick
the template from GitHub's dropdown.
-->

## Summary

<one or two sentences describing what changed and why>

## Verification

- [ ] `.venv/bin/python -m unittest discover -s tests -v` — all green
- [ ] (if any code in `scripts/aidefend_discovery/`) added or extended a unit test
- [ ] (if any docs changed) cross-links resolve, anchor slugs are valid
- [ ] (if connectors changed) live smoke run confirmed in PR comment with redacted output

## Companion changes (if any)

- [ ] `aidefense-framework` PR: <link or N/A>
- [ ] `aidefend-mcp` PR: <link or N/A>
- [ ] `agent-continuity` updates: <link or N/A>

## Notes for reviewers

<anything tricky, drift risks, secrets to rotate, follow-ups to schedule>
