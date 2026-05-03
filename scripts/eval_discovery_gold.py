#!/usr/bin/env python3
"""Compare gap_run JSON against a hand-labeled gold file (JSONL).

Each gold row supports:
  candidate_id (required): match against gap_reports[].candidate_id
  expect_is_gap (optional, bool): compared to gap_report.is_gap
  nearest_should_include_aid (optional, str | list[str]): each entry is a
    prefix-match against nearest_technique_ids; e.g., "AID-H" matches
    "AID-H-019.004". A list passes if ANY entry matches.
  rationale, labeled_by, labeled_at: documentation only.

Outputs JSON with:
  gold_rows_used, is_gap_accuracy,
  nearest_topk_hit_rate (per-row: any expected prefix appears in top_k),
  precision_is_gap, recall_is_gap, f1_is_gap (treating is_gap=True as the
  positive class).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _expected_prefixes(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value).strip()
    return [s] if s else []


def _matches_any_prefix(prefixes: list[str], nearest_ids: list[str]) -> bool:
    for p in prefixes:
        for n in nearest_ids:
            if n.startswith(p):
                return True
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate gap_run vs gold labels")
    p.add_argument("--report", type=Path, required=True, help="gap_run_*.json from reports/")
    p.add_argument("--gold", type=Path, required=True, help="JSONL with labels")
    args = p.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    by_id = {g["candidate_id"]: g for g in report.get("gap_reports", [])}

    matched = 0
    gap_total = 0
    gap_agree = 0
    nearest_total = 0
    nearest_hits = 0
    tp = fp = fn = tn = 0  # is_gap=True is the positive class

    for raw_line in args.gold.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
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
            expected = bool(row["expect_is_gap"])
            actual = bool(gr.get("is_gap"))
            if expected == actual:
                gap_agree += 1
            else:
                print(
                    f"MISMATCH is_gap: {cid} gold={expected} got={actual}",
                    file=sys.stderr,
                )
            if expected and actual:
                tp += 1
            elif expected and not actual:
                fn += 1
            elif (not expected) and actual:
                fp += 1
            else:
                tn += 1

        prefixes = _expected_prefixes(row.get("nearest_should_include_aid"))
        if prefixes:
            nearest_total += 1
            nearest_ids = gr.get("nearest_technique_ids") or []
            if _matches_any_prefix(prefixes, nearest_ids):
                nearest_hits += 1
            else:
                print(
                    f"MISMATCH nearest: {cid} want any of {prefixes!r} prefix-match in {nearest_ids[:5]}",
                    file=sys.stderr,
                )

    def _safe_div(num: float, den: float) -> float | None:
        return round(num / den, 4) if den else None

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = (
        round(2 * (precision or 0) * (recall or 0) / ((precision or 0) + (recall or 0)), 4)
        if precision and recall
        else None
    )

    out = {
        "report_path": str(args.report),
        "gold_path": str(args.gold),
        "gold_rows_used": matched,
        "is_gap_accuracy": _safe_div(gap_agree, gap_total),
        "nearest_topk_hit_rate": _safe_div(nearest_hits, nearest_total),
        "is_gap_confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision_is_gap": precision,
        "recall_is_gap": recall,
        "f1_is_gap": f1,
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
