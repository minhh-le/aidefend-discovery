from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from aidefend_discovery.bridge import (
    default_bridge_path,
    load_bridge,
    load_default_bridge_or_empty,
    suggest_from_entities,
)


_FIXTURE_YAML = """
version: "test-0.1"
generated_at: "2026-05-02"

bridges:
  - cwe_id: CWE-94
    pillar: [app, model]
    phase: [building, operation]
    suggested_tactic_ids: [harden, isolate]
    rationale: "Code injection via LLM-generated code"
    confidence: 0.85
    source: "https://cwe.mitre.org/data/definitions/94.html"

  - cwe_id: CWE-1427
    pillar: [model]
    phase: [operation]
    suggested_tactic_ids: [harden, detect]
    rationale: "Prompt injection — direct AI CWE"
    confidence: 0.95
    source: "https://cwe.mitre.org/data/definitions/1427.html"

  - cwe_id: CWE-200
    pillar: [data]
    phase: [operation]
    suggested_tactic_ids: [isolate]
    rationale: "Information disclosure"
    confidence: 0.0   # disabled
    source: "https://cwe.mitre.org/data/definitions/200.html"
"""


class TestBridgeLoad(unittest.TestCase):
    def _write(self, content: str) -> Path:
        p = Path(tempfile.mkstemp(suffix=".yaml")[1])
        p.write_text(content, encoding="utf-8")
        return p

    def test_load_valid_yaml(self) -> None:
        p = self._write(_FIXTURE_YAML)
        bridges = load_bridge(p)
        ids = [b["cwe_id"] for b in bridges]
        self.assertEqual(ids, ["CWE-94", "CWE-1427", "CWE-200"])
        self.assertEqual(bridges[0]["confidence"], 0.85)

    def test_rejects_missing_cwe_id(self) -> None:
        bad = _FIXTURE_YAML.replace("CWE-94", "INVALID-94")
        p = self._write(bad)
        with self.assertRaises(ValueError):
            load_bridge(p)

    def test_default_bridge_or_empty_safe(self) -> None:
        # Real default may or may not exist; either way we don't crash.
        out = load_default_bridge_or_empty()
        self.assertIsInstance(out, list)


class TestBridgeSuggest(unittest.TestCase):
    def setUp(self) -> None:
        p = Path(tempfile.mkstemp(suffix=".yaml")[1])
        p.write_text(_FIXTURE_YAML, encoding="utf-8")
        self.bridges = load_bridge(p)

    def test_suggests_for_known_cwe(self) -> None:
        out = suggest_from_entities({"cwes": ["CWE-94"]}, self.bridges)
        self.assertIn("app", out["pillars"])
        self.assertIn("model", out["pillars"])
        self.assertIn("harden", out["suggested_tactic_ids"])
        self.assertIn("isolate", out["suggested_tactic_ids"])
        self.assertEqual(len(out["rationales"]), 1)
        self.assertIn("CWE-94", out["rationales"][0])
        self.assertIn("conf 0.85", out["rationales"][0])

    def test_dedupes_across_multiple_cwes(self) -> None:
        out = suggest_from_entities({"cwes": ["CWE-94", "CWE-1427"]}, self.bridges)
        # 'harden' appears in both; should appear only once
        self.assertEqual(out["suggested_tactic_ids"].count("harden"), 1)
        self.assertEqual(len(out["rationales"]), 2)

    def test_unknown_cwe_returns_empty_for_that_cwe(self) -> None:
        out = suggest_from_entities({"cwes": ["CWE-9999"]}, self.bridges)
        self.assertEqual(out["pillars"], [])
        self.assertEqual(out["rationales"], [])

    def test_zero_confidence_skipped(self) -> None:
        out = suggest_from_entities({"cwes": ["CWE-200"]}, self.bridges)
        self.assertEqual(out["rationales"], [])

    def test_no_entities_safe(self) -> None:
        out = suggest_from_entities(None, self.bridges)
        self.assertEqual(out["rationales"], [])

    def test_default_bridge_yaml_loads_cleanly(self) -> None:
        """The shipped bridge YAML must parse and contain real entries."""
        path = default_bridge_path()
        if not path.exists():
            self.skipTest("default bridge not present in this checkout")
        bridges = load_bridge(path)
        self.assertGreater(len(bridges), 10)
        # Every entry must have non-empty rationale and source
        for b in bridges:
            self.assertTrue(b["rationale"], f"rationale empty for {b['cwe_id']}")
            self.assertTrue(b["source"].startswith("http"), f"source not URL for {b['cwe_id']}")
            self.assertGreater(b["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
