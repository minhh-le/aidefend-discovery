"""Tests for AIDEFEND discovery baseline, BM25, RSS parsing."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from aidefend_discovery.baseline import (
    extract_threat_ids,
    flatten_techniques,
    strip_html,
)
from aidefend_discovery.bm25_index import BM25Index
from aidefend_discovery.entities import extract_entities, merge_entity_dicts
from aidefend_discovery.explain import top_overlap_terms
from aidefend_discovery.extract import chunk_text, enrich_candidate, normalize_hostname
from aidefend_discovery.nvd_ingest import nvd_cve_to_candidate
from aidefend_discovery.rss_ingest import entry_to_candidate, parse_feed_entries
import run_discovery_gap

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestBaseline(unittest.TestCase):
    def test_flatten_minimal(self) -> None:
        data = json.loads((FIXTURES / "minimal_aidefend_data.json").read_text(encoding="utf-8"))
        rows = flatten_techniques(data)
        ids = {r.id for r in rows}
        self.assertEqual(ids, {"AID-M-TEST", "AID-M-TEST.001"})
        parent = next(r for r in rows if r.id == "AID-M-TEST.001")
        self.assertEqual(parent.parent_id, "AID-M-TEST")
        root = next(r for r in rows if r.id == "AID-M-TEST")
        self.assertTrue(any("AML.T0007" in t for t in root.threat_items))

    def test_strip_html(self) -> None:
        self.assertEqual(strip_html("<p>a &amp; b</p>").lower(), "a & b")

    def test_extract_threat_ids(self) -> None:
        s = "Maps to AML.T0007 and LLM03:2025 Supply Chain"
        got = extract_threat_ids(s)
        self.assertTrue(any("AML.T0007" in x for x in got))


class TestBM25(unittest.TestCase):
    def test_rank_inventory_query(self) -> None:
        data = json.loads((FIXTURES / "minimal_aidefend_data.json").read_text(encoding="utf-8"))
        records = flatten_techniques(data)
        corpus = [r.search_text() for r in records]
        ix = BM25Index(corpus)
        top = ix.top_k("AI asset inventory catalog visibility", 2)
        best_idx = top[0][0]
        self.assertEqual(records[best_idx].id, "AID-M-TEST")


class TestRSS(unittest.TestCase):
    def test_parse_rss_fixture(self) -> None:
        xml_bytes = (FIXTURES / "sample_rss.xml").read_bytes()
        entries = parse_feed_entries(xml_bytes, "https://example.test/feed.xml")
        self.assertEqual(len(entries), 2)
        c0 = entry_to_candidate(entries[0])
        self.assertEqual(c0["status"], "candidate")
        self.assertIn("candidate-rss-", c0["id"])
        self.assertEqual(c0["source_urls"], ["https://example.test/article/1"])
        self.assertEqual(c0.get("summary_raw"), c0.get("summary"))


class TestEntities(unittest.TestCase):
    def test_extract_cve_and_ghsa(self) -> None:
        s = "See CVE-2024-1234 and GHSA-1234-5678-abcd for CWE-79 details."
        got = extract_entities(s)
        self.assertIn("CVE-2024-1234", got["cves"])
        self.assertIn("ghsa-1234-5678-abcd", got["ghsas"])
        self.assertIn("CWE-79", got["cwes"])

    def test_merge_entity_dicts(self) -> None:
        m = merge_entity_dicts(
            {"cves": ["CVE-2024-1"], "ghsas": [], "cwes": []},
            {"cves": ["CVE-2024-1"], "ghsas": ["ghsa-abcd-ef01-2345"], "cwes": ["CWE-79"]},
        )
        self.assertEqual(len(m["cves"]), 1)
        self.assertEqual(len(m["ghsas"]), 1)

    def test_version_constraints_comparator(self) -> None:
        got = extract_entities("affected versions: < 2.0.1, fixed in 2.0.2")
        self.assertIn("< 2.0.1", got["version_constraints"])
        self.assertIn("fixed_in:2.0.2", got["version_constraints"])

    def test_version_constraints_interval(self) -> None:
        got = extract_entities("Range 1.0.0 - 2.0.1 is vulnerable; >= 1.4 also impacted.")
        self.assertIn("1.0.0 - 2.0.1", got["version_constraints"])
        self.assertIn(">= 1.4", got["version_constraints"])

    def test_version_constraints_dedup_and_normalize(self) -> None:
        got = extract_entities("Affected: 1.0.0; affected: 1.0.0; = 2.0; == 2.0")
        # affected normalized once; comparator '=' rewritten to '=='; dedup applied
        self.assertEqual(got["version_constraints"].count("affected:1.0.0"), 1)
        self.assertEqual(got["version_constraints"].count("== 2.0"), 1)

    def test_version_constraints_empty_when_absent(self) -> None:
        got = extract_entities("Plain prose with no versions whatsoever.")
        self.assertEqual(got["version_constraints"], [])


class TestExtractChunking(unittest.TestCase):
    def test_chunk_overlap(self) -> None:
        text = "x" * 5000
        chunks = chunk_text(text, chunk_size=2000, overlap=200, source_url="https://ex.test/a")
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["index"], 0)

    def test_enrich_without_fetch(self) -> None:
        c = {
            "title": "Hello",
            "summary": "World CVE-2023-9999 discussion",
            "source_urls": ["https://example.test/x"],
            "feed_url": "https://example.test/feed.xml",
            "status": "candidate",
            "license_note": "x",
            "confidence": 0.5,
            "raw_hash": "old",
            "id": "candidate-rss-old",
        }
        enrich_candidate(
            c,
            fetch_pages=False,
            host_allowlist=set(),
        )
        self.assertEqual(c.get("body_fetch_skipped_reason"), "fetch_disabled")
        self.assertIn("CVE-2023-9999", (c.get("entities") or {}).get("cves", []))
        self.assertTrue(c.get("retrieval_chunk_queries"))


class TestExplain(unittest.TestCase):
    def test_overlap_terms(self) -> None:
        corpus = ["alpha bravo delta inventory", "other"]
        ix = BM25Index(corpus)
        idf = ix.idf_vector()
        terms = top_overlap_terms("inventory alpha raretoken", corpus[0], idf, limit=5)
        self.assertIn("inventory", terms)
        self.assertIn("alpha", terms)


class TestBM25Pooled(unittest.TestCase):
    def test_top_k_pooled(self) -> None:
        corpus = ["cat dog bird", "fish snake", "cat snake"]
        ix = BM25Index(corpus)
        r = ix.top_k_pooled(["cat", "snake"], k=2)
        idxs = [i for i, _ in r]
        self.assertIn(2, idxs)


class TestHostname(unittest.TestCase):
    def test_normalize(self) -> None:
        self.assertEqual(normalize_hostname("WWW.EXAMPLE.COM:443"), "example.com")


class TestRunDiscoveryOrchestration(unittest.TestCase):
    def test_source_nvd_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            report_dir = Path(td) / "reports"
            with patch("run_discovery_gap.load_data_json", return_value={"tactics": []}), patch(
                "run_discovery_gap.flatten_techniques"
            ) as mock_flatten, patch("run_discovery_gap.BM25Index"), patch(
                "run_discovery_gap.load_host_allowlist", return_value=set()
            ), patch(
                "run_discovery_gap.ingest_allowlisted_feed"
            ) as mock_rss_ingest, patch(
                "run_discovery_gap.ingest_nvd_incremental",
                return_value=[],
                create=True,
            ) as mock_nvd_ingest:
                mock_flatten.return_value = [
                    type(
                        "Record",
                        (),
                        {
                            "search_text": lambda self: "x",
                            "id": "AID-M-TEST",
                            "tactic_id": "AID-T-TEST",
                            "pillars": [],
                            "phases": [],
                            "threat_items": [],
                        },
                    )()
                ]
                argv = [
                    "run_discovery_gap.py",
                    "--source",
                    "nvd",
                    "--data-json",
                    str(FIXTURES / "minimal_aidefend_data.json"),
                    "--reports-dir",
                    str(report_dir),
                    "--dry-run",
                ]
                with patch.object(sys, "argv", argv):
                    rc = run_discovery_gap.main()
                self.assertEqual(rc, 0)
                mock_nvd_ingest.assert_called_once()
                mock_rss_ingest.assert_not_called()


class TestNvdFlowCompatibility(unittest.TestCase):
    def test_nvd_candidates_generate_gap_report_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            report_dir = Path(td) / "reports"
            nvd_candidate = nvd_cve_to_candidate(
                {
                    "cve": {
                        "id": "CVE-2026-1234",
                        "descriptions": [{"lang": "en", "value": "Prompt injection in model serving endpoint"}],
                        "weaknesses": [{"description": [{"lang": "en", "value": "CWE-79"}]}],
                        "references": [{"url": "https://example.test/CVE-2026-1234"}],
                    }
                },
                retrieved_at="2026-05-02T00:00:00Z",
            )
            with patch("run_discovery_gap.load_data_json", return_value={"tactics": []}), patch(
                "run_discovery_gap.flatten_techniques"
            ) as mock_flatten, patch(
                "run_discovery_gap.ingest_nvd_incremental", return_value=[nvd_candidate]
            ), patch("run_discovery_gap.load_host_allowlist", return_value=set()):
                mock_flatten.return_value = [
                    type(
                        "Record",
                        (),
                        {
                            "search_text": lambda self: "prompt injection model serving",
                            "id": "AID-M-TEST",
                            "tactic_id": "AID-T-TEST",
                            "pillars": ["model"],
                            "phases": ["runtime"],
                            "threat_items": ["AML.T0007"],
                        },
                    )()
                ]
                argv = [
                    "run_discovery_gap.py",
                    "--source",
                    "nvd",
                    "--data-json",
                    str(FIXTURES / "minimal_aidefend_data.json"),
                    "--reports-dir",
                    str(report_dir),
                    "--dry-run",
                    "--no-fetch-pages",
                ]
                with patch.object(sys, "argv", argv):
                    rc = run_discovery_gap.main()
                self.assertEqual(rc, 0)
                report_path = next(report_dir.glob("gap_run_*.json"))
                payload = json.loads(report_path.read_text(encoding="utf-8"))
                self.assertEqual(len(payload["candidates"]), 1)
                self.assertEqual(len(payload["gap_reports"]), 1)
                self.assertEqual(payload["params"]["source"], "nvd")


if __name__ == "__main__":
    unittest.main()
