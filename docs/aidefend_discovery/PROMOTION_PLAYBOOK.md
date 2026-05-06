# Promotion playbook — discovery candidate → upstream `tactics/*.js`

Updated: 2026-05-05

This expands the brief promotion checklist in [`REVIEW_CONTRACT.md`](REVIEW_CONTRACT.md#promotion-checklist-into-tacticsjs) with the concrete shape mapping a maintainer needs to convert an accepted `CandidateFinding` into a framework tactic edit. It is paired with the **anchor-diff pre-flight** below: before promoting, reviewers must run the shipped taxonomy anchor diff and confirm the candidate does not already exist in upstream anchors under different wording.

The authoritative framework snapshot now lives in this monorepo under `vendor/aidefense-framework/`. It remains a tracked source snapshot from upstream, not an automatically mutated discovery output.

---

## Anchor-diff pre-flight (read this first)

The taxonomy anchor diff has shipped (`scripts/anchor_diff.py` + vendored YAMLs in `lab/aidefend_discovery/taxonomy_anchors/`). **Promotions are now allowed**, with one mandatory pre-flight: run the diff and consult its output before opening any upstream PR. Without that step, a "novel" candidate that already exists in OWASP / MAESTRO / NIST under different wording would silently fork AIDEFEND vocabulary from its upstream anchors.

```sh
python3 scripts/anchor_diff.py \
  --output reports/anchor_diff_$(date -u +%Y%m%d).json
```

Inspect the report's `present_in_aidefend[]` for the framework you're touching. If the candidate's threat name already maps to a present anchor ID, your promotion is a `defendsAgainst` extension (Shape A), not a new technique (Shape B). The vendored anchor YAMLs are point-in-time snapshots — refresh them quarterly per `QUALITY_AUDIT_CHECKLIST.md`.

---

## Pre-flight checks

Every check must pass before opening a PR upstream.

1. **Status & rationale.** `CandidateFinding.status == "candidate"`; reviewer has read `GapReport.gap_reason`, `nearest_technique_ids`, `nearest_lexical_overlap_terms`, and concurs.
2. **License.** `license_note` is permissive (e.g., CC BY, public-domain, framework license that allows redistribution of summaries) **or** the upstream PR will use only metadata + paraphrased description and will not reproduce body text. CC BY content can be used with attribution.
3. **Anchor-diff guardrail.** Run the shipped Phase 2 anchor diff and record whether the candidate is a `defendsAgainst` extension (Shape A) or a genuinely new technique candidate (Shape B).
4. **Citations resolve.** Every URL in `source_urls` is reachable; `content_hash` matches the cited content (re-fetch and compare if in doubt).
5. **Not already promoted.** Search the discovery JSONL for prior `promoted` rows touching the same `content_hash` or `entities.cves`/`entities.ghsas`.

---

## Choose the promotion shape

### Shape A — Extend an existing technique's `defendsAgainst` (most common, lowest risk)

**Trigger:** `GapReport.nearest_technique_ids[0]` is a confident match (high `max_bm25`, sensible `nearest_lexical_overlap_terms`) but the candidate's framework IDs / threat tokens don't appear under any `defendsAgainst.framework.items` of that technique.

**What you edit:** the existing technique's `defendsAgainst` array in `vendor/aidefense-framework/tactics/<tactic>.js`. Add the upstream framework ID **verbatim** under the right `framework` block. Don't rephrase — AIDEFEND's `name`/`description`/`purpose` are canonical, but `defendsAgainst.items` mirror upstream.

### Shape B — Add a new technique to a tactic file (rare)

**Trigger:** No existing technique covers the behavior — `is_gap == true` with `gap_reason` `max_bm25_below_threshold(...)`, AND the reviewer agrees no top-k neighbor is the right home.

**What you edit:** add a new `techniques[]` entry to the chosen `tactics/<tactic>.js`. Required fields are listed in the crosswalk below. Sub-techniques follow the dotted-id pattern (`AID-H-021.002`).

---

## Tactic file selection

Seven tactic files; each owns its own ID prefix:

| File | Tactic | ID prefix | Loose theme |
|---|---|---|---|
| `tactics/model.js` | Model | `AID-M-NNN` | Model-side defenses |
| `tactics/harden.js` | Harden | `AID-H-NNN` | Pre-deployment hardening |
| `tactics/detect.js` | Detect | `AID-D-NNN` | Runtime detection |
| `tactics/isolate.js` | Isolate | `AID-I-NNN` | Containment |
| `tactics/deceive.js` | Deceive | `AID-DV-NNN` | Deception (note two-letter prefix) |
| `tactics/evict.js` | Evict | `AID-E-NNN` | Removal / response |
| `tactics/restore.js` | Restore | `AID-R-NNN` | Recovery |

`GapReport.suggested_tactic_ids` (e.g., `["harden", "model"]`) is a **hint**, not a decision. `suggested_pillars` (`app | data | infra | model`) and `suggested_phases` (`building | operation | validation`) are also hints — reviewer makes the final call by reading neighbor techniques.

> **Note on file syntax.** Some tactic files (`harden.js`) use bare-key JS object literals; others (`detect.js`, `model.js`, `isolate.js`, `evict.js`, `restore.js`, `deceive.js`) use JSON-style quoted keys. Match the existing style in the file you're editing — the upstream parser in `scripts/generate-dataset.js` accepts both, but consistency matters for review.

---

## Crosswalk — `CandidateFinding` / `GapReport` → upstream technique object

Schema source: [`scripts/aidefend_discovery/schemas.py`](../../scripts/aidefend_discovery/schemas.py).

| Upstream technique field | Sourced from | Notes |
|---|---|---|
| `id` | reviewer-assigned | Next sequential under chosen tactic prefix; sub-technique uses `AID-X-NNN.NNN` |
| `name` | reviewer-rephrased from `CandidateFinding.title` | AIDEFEND wording is canonical; not a verbatim copy |
| `pillar` (string[]) | `GapReport.suggested_pillars` (hint) | Reviewer confirms by reading neighbor techniques in same file |
| `phase` (string[]) | `GapReport.suggested_phases` (hint) | Same — confirm against neighbors |
| `description` | reviewer-authored | May draw on `body_extracted` and `summary` for facts; do not reproduce non-permissive text verbatim |
| `defendsAgainst[].framework` | reviewer maps from candidate context | Use exact upstream framework names (e.g., `"MITRE ATLAS"`, `"OWASP LLM Top 10 2025"`, `"MAESTRO"`, `"NIST Adversarial Machine Learning 2025"`, etc.) |
| `defendsAgainst[].items` | `entities.cves`, `entities.ghsas`, `entities.cwes` + manual mapping to ATLAS / OWASP / NIST / MAESTRO IDs | Mirror upstream phrasing **exactly**. CVE/GHSA/CWE IDs themselves rarely belong here — translate them up to the framework-level threat name |
| `toolsOpenSource` (string[]) | reviewer research | Not in `CandidateFinding`; gather at promotion time |
| `toolsCommercial` (string[]) | reviewer research | Same |
| `implementationGuidance[].implementation` | reviewer-authored | Not in `CandidateFinding`; HTML allowed in `howTo` |
| `implementationGuidance[].howTo` | reviewer-authored | HTML; follow the prose+code style in existing entries |

For Shape A, only `defendsAgainst[].items` is touched.

### Schema-gap callouts

`CandidateFinding` does **not** carry `toolsOpenSource`, `toolsCommercial`, or `implementationGuidance`. That's expected — these are reviewer-authored at promotion time, not extracted automatically. If, while filling out a Shape B promotion, you find a *required* technique field that has no clear source in `CandidateFinding` and is not naturally reviewer-authored, **stop the promotion and open a Phase 1 schema gap issue.** The `CandidateFinding` schema is the wire format for the whole pipeline; gaps caught at promotion time are cheaper to fix than gaps caught after MCP integration.

Newer fields in `CandidateFinding` worth knowing about (added with the Phase 2A NVD connector):

- `source_type` — `"rss"`, `"nvd"`, etc. Useful in PR description.
- `source_id` — connector-native ID (e.g., the CVE ID for NVD candidates).
- `kev_flag` — `true` if the source signals KEV (Known Exploited Vuln). Strong promotion signal; mention explicitly in PR description.

---

## PR description template

Open the PR against `aidefense-framework`. Use this template so promotion is auditable and the discovery loop can be measured:

```markdown
## Discovery promotion — <candidate title>

- **Discovery candidate:** `<candidate_id>` (`source_type=<rss|nvd|...>`, `source_id=<...>`)
- **Source URLs:** <one bullet per source_urls entry>
- **content_hash:** `<content_hash>`
- **GapReport summary:**
  - `nearest_technique_ids`: <top-5>
  - `max_bm25`: <value>
  - `gap_reason`: `<gap_reason>`
  - `nearest_lexical_overlap_terms`: <flatten top-1>
- **Promotion shape:** A (extend defendsAgainst) | B (new technique)
- **Anchor-diff status:** shipped | manual-check-recorded-below
- **kev_flag:** true | false
- **Reviewer notes:** <why this shape, why this pillar/phase, any framework-ID disambiguation>

Closes loop for: <discovery JSONL row id>
```

---

## Step-by-step

1. **Pick a candidate** from `reports/gap_run_*.json` whose paired `CandidateFinding` has `status: "candidate"`.
2. **Pre-flight checks** above all pass.
3. **Choose Shape A or B.**
4. **Edit `vendor/aidefense-framework/tactics/<tactic>.js`** matching the existing file's syntax style. For Shape A: add `defendsAgainst.items` only. For Shape B: full new technique entry per crosswalk.
5. **Regenerate** `data/data.json`:
   ```sh
   cd vendor/aidefense-framework && node scripts/generate-dataset.js
   ```
   The generator is fail-closed on keywords (see header of `generate-dataset.js`); resolve any keyword-lock failures per upstream guidance, do not bypass.
6. **Smoke-test from the discovery side.** Re-run the gap pipeline against the regenerated baseline; the same candidate should now resolve to the new/extended technique with `is_gap == false`:
   ```sh
   python scripts/run_discovery_gap.py \
     --feed-url https://github.com/langchain-ai/langchain/releases.atom \
     --allowlist lab/aidefend_discovery/feeds.allowlist \
     --max-items 1
   ```
   If the candidate still reports `is_gap == true` against the same technique, the upstream edit didn't land where retrieval can see it — investigate before opening the PR.
7. **Open the upstream PR** using the template above.
8. **After merge,** append a `promoted` row update to the discovery JSONL with the merged PR URL and the upstream commit SHA in reviewer notes (see [`REVIEW_CONTRACT.md`](REVIEW_CONTRACT.md) status workflow).

---

## What success looks like (Phase 1 exit)

Phase 1 of the [`ROADMAP`](ROADMAP.md#phase-1--interpretable-signal) exits when **one** credible "candidate ↔ defenses *because…*" story has been demoed **and** the resulting upstream PR is merged. Not "the report rendered" — the loop closing end-to-end is the bar, because that is the only honest signal that `is_gap` produces things maintainers want.
