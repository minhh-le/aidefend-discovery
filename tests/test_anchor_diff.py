from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import anchor_diff


_ANCHOR_YAML = """
framework: "Test Framework"
version: "1.0"
source_url: "https://example.test/framework"
snapshot_date: "2026-05-03"

items:
  - id: "TF-01"
    title: "First"
  - id: "TF-02"
    title: "Second (covered)"
  - id: "TF-99"
    title: "Missing in AIDEFEND"
"""

_DATA_JSON = {
    "tactics": [
        {
            "techniques": [
                {
                    "id": "AID-H-T1",
                    "defendsAgainst": [
                        {
                            "framework": "Test Framework",
                            "items": [
                                "TF-01 First (extra phrasing)",
                                "TF-02 Second covered",
                                "TF-NOTANCHOR Some upstream-only thing",
                            ],
                        }
                    ],
                    "subTechniques": [
                        {
                            "id": "AID-H-T1.001",
                            "defendsAgainst": [
                                {
                                    "framework": "Test Framework",
                                    "items": ["TF-01 alternate phrasing"],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    ]
}


class TestAnchorDiff(unittest.TestCase):
    def test_substring_match_identifies_present_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            yml = Path(td) / "tf.yaml"
            yml.write_text(_ANCHOR_YAML, encoding="utf-8")

            anchor = anchor_diff.load_anchor_yaml(yml)
            upstream = anchor_diff.collect_aidefend_items(_DATA_JSON)
            ai = upstream["Test Framework"]
            d = anchor_diff.diff_anchor(anchor, ai)

            present_ids = [p["id"] for p in d["present_in_aidefend"]]
            missing_ids = [m["id"] for m in d["missing_from_aidefend"]]

            self.assertIn("TF-01", present_ids)
            self.assertIn("TF-02", present_ids)
            self.assertIn("TF-99", missing_ids)
            self.assertEqual(d["coverage_ratio"], round(2 / 3, 4))

    def test_collect_traverses_nested_subtechniques(self) -> None:
        upstream = anchor_diff.collect_aidefend_items(_DATA_JSON)
        # Both top-level and sub-technique items contribute
        items = upstream["Test Framework"]
        self.assertTrue(any("TF-01 First" in x for x in items))
        self.assertTrue(any("TF-01 alternate" in x for x in items))

    def test_unmatched_aidefend_items_surfaced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            yml = Path(td) / "tf.yaml"
            yml.write_text(_ANCHOR_YAML, encoding="utf-8")
            anchor = anchor_diff.load_anchor_yaml(yml)
            upstream = anchor_diff.collect_aidefend_items(_DATA_JSON)
            d = anchor_diff.diff_anchor(anchor, upstream["Test Framework"])
            # TF-NOTANCHOR is in AIDEFEND but not in our anchor → surfaced
            self.assertTrue(
                any("TF-NOTANCHOR" in s for s in d["unmatched_aidefend_items"])
            )

    def test_anchor_yaml_validation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.yaml"
            bad.write_text("framework: Test\n# missing items\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                anchor_diff.load_anchor_yaml(bad)

    def test_default_anchors_dir_loads(self) -> None:
        """All shipped anchor YAMLs must parse and declare framework + items."""
        anchors_dir = _REPO_ROOT / "lab" / "aidefend_discovery" / "taxonomy_anchors"
        if not anchors_dir.exists():
            self.skipTest("anchors dir not present")
        loaded = 0
        for yml in anchors_dir.glob("*.yaml"):
            data = anchor_diff.load_anchor_yaml(yml)
            self.assertTrue(data.get("framework"))
            self.assertGreater(len(data.get("items") or []), 0)
            loaded += 1
        self.assertGreaterEqual(loaded, 6, "expected at least 6 vendored anchors")


if __name__ == "__main__":
    unittest.main()
