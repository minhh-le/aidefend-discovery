#!/usr/bin/env python3
"""Emit discovery pipeline metrics from the sqlite candidate store.

Currently reports: total candidates, by-status counts, runs count, gap-report
count, distinct candidates with `is_gap=true`, gap rate, promotion rate.

Usage:
  python3 scripts/discovery_metrics.py \\
    --state-db lab/aidefend_discovery/discovery_state.db \\
    --output reports/metrics_$(date -u +%Y%m%d).json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from aidefend_discovery.state_store import candidate_counts  # noqa: E402


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
        default=ROOT / "reports" / f"metrics_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json",
    )
    args = parser.parse_args(argv)

    if not args.state_db.exists():
        print(f"ERROR: state_db not found: {args.state_db}", file=sys.stderr)
        return 1

    counts = candidate_counts(args.state_db)
    total = max(1, counts["total"])  # avoid div-by-zero
    metrics = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state_db": str(args.state_db),
        "counts": counts,
        "rates": {
            "is_gap_rate": round(counts["is_gap_true"] / total, 4),
            "promotion_rate": round(counts["status_promoted"] / total, 4),
            "rejection_rate": round(counts["status_rejected"] / total, 4),
            "candidate_pending_rate": round(counts["status_candidate"] / total, 4),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote metrics to {args.output}", file=sys.stderr)
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
