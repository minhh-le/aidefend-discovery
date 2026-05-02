from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from aidefend_discovery.nvd_ingest import (
    build_nvd_query,
    ingest_nvd_incremental,
    nvd_cve_to_candidate,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestNvdQuery(unittest.TestCase):
    def test_build_query_requires_both_dates(self) -> None:
        with self.assertRaises(ValueError):
            build_nvd_query(lastmod_start="2026-01-01T00:00:00Z", lastmod_end=None)

    def test_build_query_rejects_too_wide_window(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = start + timedelta(days=121)
        with self.assertRaises(ValueError):
            build_nvd_query(
                lastmod_start=start.isoformat().replace("+00:00", "Z"),
                lastmod_end=end.isoformat().replace("+00:00", "Z"),
            )

    def test_build_query_includes_pagination(self) -> None:
        query = build_nvd_query(
            lastmod_start="2026-01-01T00:00:00Z",
            lastmod_end="2026-01-10T00:00:00Z",
            start_index=2000,
            results_per_page=500,
            keyword="langchain",
        )
        self.assertEqual(query["startIndex"], 2000)
        self.assertEqual(query["resultsPerPage"], 500)
        self.assertEqual(query["keywordSearch"], "langchain")


class TestNvdParsing(unittest.TestCase):
    def test_normalize_cve_to_candidate(self) -> None:
        payload = json.loads((FIXTURES / "nvd_api_sample.json").read_text(encoding="utf-8"))
        item = payload["vulnerabilities"][0]
        candidate = nvd_cve_to_candidate(item)
        self.assertEqual(candidate["status"], "candidate")
        self.assertEqual(candidate["feed_url"], "nvd_api")
        self.assertEqual(candidate["source_type"], "nvd_api")
        self.assertEqual(candidate["source_id"], "CVE-2026-1234")
        self.assertIn("CVE-2026-1234", candidate["entities"]["cves"])
        self.assertIn("CWE-79", candidate["entities"]["cwes"])
        self.assertTrue(candidate["source_urls"])

    def test_incremental_ingest_pages(self) -> None:
        payload = json.loads((FIXTURES / "nvd_api_sample.json").read_text(encoding="utf-8"))
        rows = ingest_nvd_incremental(
            lastmod_start="2026-01-01T00:00:00Z",
            lastmod_end="2026-01-10T00:00:00Z",
            results_per_page=1,
            max_pages=1,
            fetch_page_fn=lambda query, timeout_s: payload,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_type"], "nvd_api")


if __name__ == "__main__":
    unittest.main()
