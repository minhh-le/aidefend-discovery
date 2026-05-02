# Gold labels (evaluation)

Hand-curate a small JSONL file where each line is one object:

| Field | Required | Meaning |
|--------|-----------|---------|
| `candidate_id` | yes | Must match `gap_reports[].candidate_id` after a run (enrichment changes ids from feed-only hash—re-copy ids from latest `gap_run_*.json`). |
| `expect_is_gap` | no | If set, compared to `is_gap` in the report. |
| `nearest_should_include_aid` | no | If set, that `AID-*` id must appear in `nearest_technique_ids`. |

Example file: `example_labels.jsonl` (synthetic ids—replace after you label a real run).

```bash
python3 scripts/eval_discovery_gold.py \
  --report reports/gap_run_YYYYMMDD.json \
  --gold lab/aidefend_discovery/gold/example_labels.jsonl
```

Grow this set toward 20–50 rows per [ROADMAP](../../docs/aidefend_discovery/ROADMAP.md) Phase 1.
