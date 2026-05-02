#!/usr/bin/env python3
"""Compare gap_run JSON against a small hand-labeled gold file (JSONL)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate gap_run vs gold labels")
    p.add_argument("--report", type=Path, required=True, help="gap_run_*.json from reports/")
    p.add_argument("--gold", type=Path, required=True, help="JSONL with labels (see lab/aidefend_discovery/gold/)")
    args = p.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    by_id = {g["candidate_id"]: g for g in report.get("gap_reports", [])}

    matched = 0
    gap_agree = 0
    gap_total = 0
    nearest_hits = 0
    nearest_total = 0

    for line in args.gold.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        row = json.loads(line)
        cid = row.get("candidate_id")
        if not cid or cid not in by_id:
            print(f"SKIP: no gap_report for candidate_id={cid!r}", file=sys.stderr)
            continue
        matched += 1
        gr = by_id[cid]
        if "expect_is_gap" in row:
            gap_total += 1
            if bool(gr.get("is_gap")) == bool(row["expect_is_gap"]):
                gap_agree += 1
            else:
                print(
                    f"MISMATCH is_gap: {cid} gold={row['expect_is_gap']} got={gr.get('is_gap')}",
                    file=sys.stderr,
                )
        aid = row.get("nearest_should_include_aid")
        if aid:
            nearest_total += 1
            nearest_ids = gr.get("nearest_technique_ids") or []
            if aid in nearest_ids:
                nearest_hits += 1
            else:
                print(
                    f"MISMATCH nearest: {cid} want {aid} in top got {nearest_ids[:5]}",
                    file=sys.stderr,
                )

    print(
        json.dumps(
            {
                "gold_rows_used": matched,
                "is_gap_accuracy": gap_agree / gap_total if gap_total else None,
                "nearest_topk_hit_rate": nearest_hits / nearest_total if nearest_total else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
