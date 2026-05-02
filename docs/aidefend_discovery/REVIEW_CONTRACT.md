# Discovery review contract

Defines **statuses**, **rejection reasons**, and **promotion** from discovery candidates into authoritative AIDEFEND content.

Authoritative techniques live upstream in **aidefense-framework** tactic modules, not in this repo:

- Canonical edits: [`tactics/*.js`](https://github.com/edward-playground/aidefense-framework/tree/main/tactics) (e.g. `model.js`, `harden.js`, …).
- Regenerated dataset: run `node scripts/generate-dataset.js` there to refresh [`data/data.json`](https://github.com/edward-playground/aidefense-framework/blob/main/data/data.json).

This repo only produces **candidates** and **gap reports**.

---

## Record types

### CandidateFinding (ingestion)

| Field | Notes |
|-------|--------|
| `id` | Stable hash-derived id (`candidate-rss-…`). |
| `status` | `candidate` → `rejected` \| `promoted` (after human decision). |
| `title`, `summary` | Plain text; cite `source_urls`. |
| `source_urls` | Required for audit trail. |
| `retrieved_at` | ISO 8601 UTC. |
| `license_note` | Required reminder; ingestion defaults to third-party disclaimer. |
| `confidence` | Heuristic only; not approval. |
| `raw_hash` | Integrity of canonical normalized input (includes `summary_raw` + extracted body + entity line when Phase 1 enrichment runs). |
| `summary_raw`, `body_extracted`, `retrieval_chunks`, `entities` | Phase 1 fields for audit and retrieval; see `scripts/aidefend_discovery/extract.py`. |

### GapReport (retrieval)

See [`schemas.py`](../../scripts/aidefend_discovery/schemas.py) (`GapReport`). `is_gap` is true when BM25 max score is below the CLI threshold **or** extracted framework-like tokens appear in the candidate but do not match any `defendsAgainst` substring in the baseline snapshot.

---

## Status workflow

```text
candidate ──► rejected     (terminal; record reason code + optional note)
     │
     └──► promoted ──► manual edit in aidefense-framework tactics/*.js + regenerate data.json
```

- **candidate**: default from ingestion.
- **rejected**: will not be merged into AIDEFEND; keep row for metrics.
- **promoted**: maintainer committed upstream mapping or new technique; link PR/issue from notes.

---

## Rejection reason codes

Use exactly one primary code (extend via PR if needed):

| Code | When to use |
|------|-------------|
| `duplicate` | Same ground truth as an existing candidate or existing technique coverage. |
| `low_quality` | Spam, empty, off-topic, or unusable text. |
| `license` | Cannot cite or redistribute summarized content under project policy. |
| `out_of_scope` | Not AI/ML/agent security relevant for AIDEFEND. |
| `already_covered` | Lexical/threat overlap shows existing `AID-*` coverage is sufficient. |
| `false_positive` | Gap detector wrong; technique mapping exists after deeper review. |
| `needs_corroboration` | Interesting but single-source or weak evidence; hold for later. |
| `other` | Free-text explanation required in reviewer notes. |

---

## Promotion checklist (into `tactics/*.js`)

1. **Locate tactic file** — Choose Model / Harden / Detect / Isolate / Deceive / Evict / Restore alignment (`tactics/<tactic>.js`).
2. **Match shape** — Copy an existing `techniques[]` entry structure (id pattern `AID-<tactic>-###`, optional `subTechniques`, `pillar`, `phase`, `defendsAgainst`, keywords per upstream generator rules).
3. **Threat mappings** — Prefer **verbatim framework IDs and titles** from official sources when adding `defendsAgainst` lines.
4. **Keywords** — Follow aidefense-framework keyword lock policy (`scripts/generate-dataset.js` fail-closed behavior).
5. **Build** — `node scripts/generate-dataset.js` and commit updated `data/data.json` per upstream conventions.
6. **Traceability** — In PR description, link discovery `candidate_id`, sources, and reviewer.

---

## MCP / API surfacing

Candidates must remain **namespaced and explicit** if exposed alongside official techniques (see [MAINTAINER_ALIGNMENT.md](MAINTAINER_ALIGNMENT.md)): optional tools only, never mixed with curated technique IDs without labeling.
