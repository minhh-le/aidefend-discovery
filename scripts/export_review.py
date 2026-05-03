#!/usr/bin/env python3
"""Export the discovery candidate store to a review-friendly CSV.

Columns: candidate_id, status, source_type, source_id, feed_url, retrieved_at,
max_bm25, is_gap, gap_reason, suggested_tactic_ids, bridge_rationales,
source_urls, promoted_pr_url, rejected_reason.

Usage:
  python3 scripts/export_review.py \\
    --state-db lab/aidefend_discovery/discovery_state.db \\
    --output reports/review_$(date -u +%Y%m%d).csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from aidefend_discovery.state_store import iter_export_rows  # noqa: E402

COLUMNS = [
    "candidate_id",
    "status",
    "source_type",
    "source_id",
    "feed_url",
    "retrieved_at",
    "max_bm25",
    "is_gap",
    "gap_reason",
    "suggested_tactic_ids",
    "bridge_rationales",
    "source_urls",
    "promoted_pr_url",
    "rejected_reason",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-db",
        type=Path,
        default=ROOT / "lab" / "aidefend_discovery" / "discovery_state.db",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / f"review_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv",
    )
    args = parser.parse_args(argv)

    if not args.state_db.exists():
        print(f"ERROR: state_db not found: {args.state_db}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with args.output.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in iter_export_rows(args.state_db):
            w.writerow({k: row.get(k, "") for k in COLUMNS})
            rows_written += 1

    print(f"Wrote {rows_written} row(s) to {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
