#!/usr/bin/env python3
"""Diff vendored taxonomy anchor IDs against AIDEFEND `data.json` defendsAgainst.

Architectural answer to taxonomy drift (see docs/aidefend_discovery/ROADMAP.md
"Deferred with reasoning"). Each vendored anchor YAML in
lab/aidefend_discovery/taxonomy_anchors/ declares a framework + version +
items[]; this script substring-matches each item ID against the upstream
`defendsAgainst[*].items[*]` strings and reports:

  - missing_from_aidefend[]: anchor IDs not found anywhere in defendsAgainst
    (regression candidates — upstream framework has it; AIDEFEND doesn't).
  - present_in_aidefend[]: anchor IDs that match (sanity coverage).
  - unmatched_aidefend_items[]: defendsAgainst items under that framework
    that don't correspond to any anchor ID (possibly stale upstream IDs or
    AIDEFEND wording drift).

Usage:
  python3 scripts/anchor_diff.py \\
    --anchors-dir lab/aidefend_discovery/taxonomy_anchors \\
    --output reports/anchor_diff_$(date -u +%Y%m%d).json

Exit codes:
  0 — diff completed cleanly (regardless of whether regressions were found).
  1 — IO/parse error; output not written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DEFAULT_DATA_JSON = ROOT / "vendor" / "aidefense-framework" / "data" / "data.json"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:
    print("ERROR: pyyaml is required. Install via `pip install pyyaml`.", file=sys.stderr)
    sys.exit(1)


def load_anchor_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not data.get("framework"):
        raise ValueError(f"{path}: missing required 'framework' field")
    if not isinstance(data.get("items"), list):
        raise ValueError(f"{path}: missing required 'items' list")
    # Stamp content hash for replayability.
    raw = path.read_bytes()
    data["_content_hash"] = hashlib.sha256(raw).hexdigest()
    data["_path"] = str(path)
    return data


def collect_aidefend_items(data_json: dict[str, Any]) -> dict[str, list[str]]:
    """Collect upstream defendsAgainst items keyed by framework name."""
    out: dict[str, list[str]] = {}
    techniques = data_json.get("techniques") or []
    if not techniques:
        # Fallback: tactics may carry techniques nested
        for tactic in data_json.get("tactics") or []:
            techniques.extend(tactic.get("techniques") or [])
    seen: dict[str, set[str]] = {}

    def absorb(tech: dict[str, Any]) -> None:
        for da in tech.get("defendsAgainst") or []:
            framework = str(da.get("framework", "")).strip()
            if not framework:
                continue
            seen.setdefault(framework, set())
            for item in da.get("items") or []:
                s = str(item).strip()
                if s:
                    seen[framework].add(s)
        # Recurse into sub-techniques
        for sub in tech.get("subTechniques") or []:
            absorb(sub)

    for tech in techniques:
        absorb(tech)

    for fw, items in seen.items():
        out[fw] = sorted(items)
    return out


def diff_anchor(anchor: dict[str, Any], aidefend_items: list[str]) -> dict[str, Any]:
    """For a single anchor YAML, compare its items[] vs the upstream items list.

    Substring match — an anchor ID is "present" if its `id` appears as a
    substring of any aidefend_item, OR vice versa (handles both
    "AML.T0007 Search Application Repositories" upstream and bare
    "AML.T0007" in the anchor).
    """
    anchor_items = anchor.get("items") or []
    missing: list[dict[str, str]] = []
    present: list[dict[str, str]] = []
    matched_aidefend: set[str] = set()

    for entry in anchor_items:
        anchor_id = str(entry.get("id", "")).strip()
        if not anchor_id:
            continue
        anchor_id_low = anchor_id.lower()
        hit: str | None = None
        for ai in aidefend_items:
            ai_low = ai.lower()
            if anchor_id_low in ai_low or ai_low in anchor_id_low:
                hit = ai
                matched_aidefend.add(ai)
                break
        if hit is None:
            missing.append({"id": anchor_id, "title": str(entry.get("title", ""))})
        else:
            present.append({"id": anchor_id, "matched": hit})

    unmatched_aidefend = sorted(set(aidefend_items) - matched_aidefend)

    return {
        "framework": anchor["framework"],
        "version": anchor.get("version"),
        "snapshot_date": anchor.get("snapshot_date"),
        "source_url": anchor.get("source_url"),
        "anchor_path": anchor["_path"],
        "anchor_content_hash": anchor["_content_hash"],
        "anchor_item_count": len(anchor_items),
        "aidefend_item_count": len(aidefend_items),
        "missing_from_aidefend": missing,
        "present_in_aidefend": present,
        "unmatched_aidefend_items": unmatched_aidefend,
        "coverage_ratio": (
            round(len(present) / max(1, len(anchor_items)), 4)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-json",
        type=Path,
        default=DEFAULT_DATA_JSON,
        help="Path to AIDEFEND framework data/data.json (default: bundled vendor snapshot)",
    )
    parser.add_argument(
        "--anchors-dir",
        type=Path,
        default=ROOT / "lab" / "aidefend_discovery" / "taxonomy_anchors",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "reports"
        / f"anchor_diff_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json",
    )
    args = parser.parse_args(argv)

    if not args.data_json.exists():
        print(f"ERROR: data.json not found: {args.data_json}", file=sys.stderr)
        return 1
    if not args.anchors_dir.exists():
        print(f"ERROR: anchors dir not found: {args.anchors_dir}", file=sys.stderr)
        return 1

    data = json.loads(args.data_json.read_text(encoding="utf-8"))
    upstream_by_fw = collect_aidefend_items(data)
    print(
        f"INFO: loaded {sum(len(v) for v in upstream_by_fw.values())} defendsAgainst "
        f"items across {len(upstream_by_fw)} frameworks from {args.data_json}",
        file=sys.stderr,
    )

    diffs: list[dict[str, Any]] = []
    for yml in sorted(args.anchors_dir.glob("*.yaml")):
        try:
            anchor = load_anchor_yaml(yml)
        except Exception as e:
            print(f"WARN: skipping {yml}: {e}", file=sys.stderr)
            continue
        fw = anchor["framework"]
        aidefend_items = upstream_by_fw.get(fw, [])
        diffs.append(diff_anchor(anchor, aidefend_items))

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_json": str(args.data_json.resolve()),
        "anchors_dir": str(args.anchors_dir.resolve()),
        "framework_count": len(diffs),
        "total_anchor_items": sum(d["anchor_item_count"] for d in diffs),
        "total_missing": sum(len(d["missing_from_aidefend"]) for d in diffs),
        "diffs": diffs,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"INFO: anchor diff: {payload['total_missing']} regression candidates "
        f"across {payload['framework_count']} frameworks → {args.output}",
        file=sys.stderr,
    )
    # Print short summary to stdout for quick scanning
    for d in diffs:
        if d["missing_from_aidefend"]:
            print(
                f"{d['framework']}: missing {len(d['missing_from_aidefend'])}/{d['anchor_item_count']} "
                f"(coverage {d['coverage_ratio']:.0%})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
