# Quality Audit Checklist — quarterly

Updated: 2026-05-03

This checklist is the durable maintenance ritual for the AIDEFEND Discovery
layer. Run it once per quarter (or after any major framework refresh) and
attach the filled-out copy to a PR labeled `audit:Q<N>`.

The output of each audit becomes the input to the next phase of work — if
metrics regress, the runbook below points to the right deferral re-open
trigger in [`ROADMAP.md`](ROADMAP.md#deferred-with-reasoning).

## Section 1 — Gold-set precision/recall

Run:
```bash
.venv/bin/python scripts/eval_discovery_gold.py \
  --report reports/gap_run_<latest>.json \
  --gold lab/aidefend_discovery/gold/example_labels.jsonl
```

- [ ] `is_gap_accuracy` ≥ 0.70 — if no, see "Threshold tuning" below.
- [ ] `nearest_topk_hit_rate` ≥ 0.80 — if no, BM25 is broken; check baseline corpus build.
- [ ] `recall_is_gap` ≥ 0.50 — if no, **re-open trigger fired**: ROADMAP "Deferred with reasoning" → embeddings + cross-encoder rerank.
- [ ] Gold set size ≥ 50 rows — if no, append more rows from the latest run before drawing conclusions.

## Section 2 — Anchor-diff regressions

Run:
```bash
.venv/bin/python scripts/anchor_diff.py \
  --data-json /path/to/aidefense-framework/data/data.json \
  --output reports/anchor_diff_$(date -u +%Y%m%d).json
```

- [ ] Per-framework `coverage_ratio` recorded in audit PR.
- [ ] Frameworks below 80% coverage: list `missing_from_aidefend[]` items and assign each to one of:
  - **Promote** — open Shape-A `defendsAgainst` extension PR upstream.
  - **Refresh anchor** — vendored YAML is stale; pull current upstream artifact.
  - **Drift acknowledged** — upstream renamed; bump anchor's snapshot_date and content_hash.
- [ ] Each vendored anchor YAML's `snapshot_date` ≤ 6 months old. If older, refresh.
- [ ] Anchor `_content_hash` matches re-fetched upstream content (where machine-readable).

## Section 3 — Feed allowlist freshness

Run:
```bash
.venv/bin/python scripts/audit_feeds.py
```

- [ ] All feeds in `lab/aidefend_discovery/feeds.allowlist` reachable (200/304).
- [ ] Any feed with `latency_ms` > 10000 → investigate or replace.
- [ ] At least one feed with non-null `last_modified` in last 30 days (proves the source is alive).
- [ ] Page-fetch allowlist (`page_fetch.allowlist`) hosts respect robots.txt as of audit date.

## Section 4 — License posture review

- [ ] Every connector's `license_note` field still accurately describes the source's license/redistribution boundary.
- [ ] If any candidate was promoted upstream this quarter that included body text (not just metadata), confirm the source's license permits it.
- [ ] `DISCOVERY_DB_PATH` exposure: if MCP / public surfaces ship this quarter, the `is_gap_confusion` block should not include false-positive promotions of non-permissive content. **Re-open trigger** for honor-system → typed `license_note`.

## Section 5 — Accept/reject calibration

Sample 20 random rows from the past quarter's `candidates`:
```bash
.venv/bin/python -c "
import sqlite3, random
c = sqlite3.connect('lab/aidefend_discovery/discovery_state.db')
rows = [r for r in c.execute('SELECT id, status FROM candidates ORDER BY retrieved_at DESC LIMIT 200')]
random.seed(42); print('\n'.join(f'{r[0]} {r[1]}' for r in random.sample(rows, 20)))
"
```

- [ ] Manual recheck: % of `rejected` rows where reviewer would re-reject = recall.
- [ ] % of `candidate` (still pending) older than 30 days — staleness signal; consider auto-archive.
- [ ] % of `promoted` rows where the PR landed cleanly upstream (no re-review).

## Section 6 — Threshold tuning

If `is_gap_accuracy` < 0.70 or `recall_is_gap` < 0.50:

- [ ] Compute BM25 score histogram across last quarter's candidates.
- [ ] Try two alternate `--gap-bm25-max` values (e.g., median × 0.5, median × 1.5).
- [ ] Re-run gold eval at each; pick the threshold maximizing F1.
- [ ] If best F1 still < 0.5, that's the **embeddings re-open trigger**.

## Section 7 — Continuity packet drift

- [ ] `.ai/CURRENT.md`, `.ai/HANDOFF.md`, `.ai/OPEN_LOOPS.md` reflect actual repo state.
- [ ] `agent-continuity/.ai/EFFORTS.md` `aidefend-discovery-mesh` `next_action` is current.
- [ ] `python3 ../agent-continuity/scripts/closeout_check.py /home/minh/Desktop/repos/aidefend-discovery` returns PASS.
- [ ] `python3 ../agent-continuity/scripts/validate_continuity.py` returns PASS.

## Section 8 — Output

PR title: `audit: Q<N> 2026-MM-DD`

PR body sections:
1. Filled checklist (Sections 1–7).
2. Top 3 surfaced regressions or follow-ups.
3. Re-open triggers fired this quarter, with the corresponding ROADMAP item linked.
4. Recommended scope for the next quarter.
