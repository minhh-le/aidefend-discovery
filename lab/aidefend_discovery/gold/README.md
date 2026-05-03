# Gold labels (evaluation)

Hand-curated JSONL where each line is one labeling decision. Each row
documents a reviewer's call on whether a real candidate from a `gap_run`
report should be flagged as a gap and (optionally) which AID-* tactic
family it should map to.

## Row schema

| Field | Required | Type | Meaning |
|---|---|---|---|
| `candidate_id` | yes | string | Must match `gap_reports[].candidate_id` after a run. |
| `source_id` | no | string | The connector-native ID (CVE/GHSA/etc.) — for human reading. |
| `expect_is_gap` | no | bool | Compared to `is_gap` in the report. |
| `nearest_should_include_aid` | no | string \| string[] | One or more AID-* prefixes; **prefix match** — e.g., `"AID-H"` matches `"AID-H-019.004"`. List passes if ANY entry matches. |
| `rationale` | yes | string | One-line "X because Y" — auditable, rebuttable. |
| `labeled_by` | yes | string | Reviewer identity. |
| `labeled_at` | yes | string | ISO 8601 UTC. |

## Workflow

1. Run a connector to produce candidates + a gap report:
   ```bash
   NVD_API_KEY=... python3 scripts/run_discovery_gap.py --source nvd --max-items 30 ...
   GH_PAT_FOR_GHSA=... python3 scripts/run_discovery_gap.py --source ghsa --max-items 30 ...
   ```
2. For each candidate, read the title/summary/entities and the gap report's
   `nearest_technique_ids` + `bridge_rationales`. Decide:
   - Is this candidate AI-defensive in scope? If not, **`expect_is_gap: true`** with rationale "out_of_scope".
   - Does the BM25 nearest tactic family make sense? If yes, label
     **`nearest_should_include_aid`** with the AID-* prefix you'd accept.
3. Record rationale, labeler, timestamp.

## Run the eval

```bash
python3 scripts/eval_discovery_gold.py \
  --report reports/gap_run_YYYYMMDD.json \
  --gold lab/aidefend_discovery/gold/example_labels.jsonl
```

Outputs JSON with `is_gap_accuracy`, `nearest_topk_hit_rate`, and
precision/recall/F1 for the `is_gap=True` positive class.

## Soft targets (Phase 1+)

| Metric | Target | Why |
|---|---|---|
| `is_gap_accuracy` | ≥ 0.70 | At 25 rows. |
| `nearest_topk_hit_rate` | ≥ 0.80 | Catches if BM25 retrieval breaks. |
| `recall_is_gap` | ≥ 0.50 | If much lower, threshold/scope-classifier needs tuning. |

## Current set

`example_labels.jsonl` carries 25 rows produced 2026-05-03 from real
authenticated NVD + GHSA pulls (windows: 2026-04-15 → 2026-05-01).
Class balance: 19 covered / 6 genuine gaps. `labeling_log.md` summarises
each row in table form for quick scanning.

Grow toward 50+ rows per [ROADMAP](../../docs/aidefend_discovery/ROADMAP.md)
Phase 5 (quarterly quality audit). Add new rows by appending to the JSONL —
never edit historical rows; audit trail must be immutable.
