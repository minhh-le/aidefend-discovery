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

from unittest import mock
from urllib.error import HTTPError

from aidefend_discovery.nvd_ingest import (
    build_nvd_query,
    fetch_nvd_page,
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


class TestNvdAuthRetry(unittest.TestCase):
    """Auth-header injection and retry-with-backoff behavior of fetch_nvd_page."""

    def _stub_response(self, payload: bytes):
        m = mock.MagicMock()
        m.read.return_value = payload
        m.__enter__.return_value = m
        m.__exit__.return_value = False
        return m

    def test_apikey_header_set_when_env_present(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            return self._stub_response(b'{"vulnerabilities": []}')

        with mock.patch.dict("os.environ", {"NVD_API_KEY": "test-key-abc"}, clear=False):
            with mock.patch("aidefend_discovery.nvd_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                fetch_nvd_page(
                    {"lastModStartDate": "2026-01-01T00:00:00Z", "lastModEndDate": "2026-01-02T00:00:00Z", "startIndex": 0, "resultsPerPage": 1},
                )
        # urllib lowercases header keys when fetched via .headers.items()
        self.assertEqual(captured["headers"].get("Apikey"), "test-key-abc")

    def test_no_apikey_when_env_absent(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            return self._stub_response(b'{"vulnerabilities": []}')

        env_no_key = {k: v for k, v in __import__("os").environ.items() if k != "NVD_API_KEY"}
        with mock.patch.dict("os.environ", env_no_key, clear=True):
            with mock.patch("aidefend_discovery.nvd_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                fetch_nvd_page(
                    {"lastModStartDate": "2026-01-01T00:00:00Z", "lastModEndDate": "2026-01-02T00:00:00Z", "startIndex": 0, "resultsPerPage": 1},
                )
        self.assertNotIn("Apikey", captured["headers"])

    def test_retries_on_403_then_succeeds(self) -> None:
        slept: list[float] = []

        def fake_sleep(s: float) -> None:
            slept.append(s)

        call_count = {"n": 0}

        def fake_urlopen(req, timeout):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise HTTPError(req.full_url, 403, "rate limited", {"Retry-After": "0"}, None)
            return self._stub_response(b'{"vulnerabilities": [{"cve":{"id":"CVE-2026-1"}}]}')

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("aidefend_discovery.nvd_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                payload = fetch_nvd_page(
                    {"lastModStartDate": "2026-01-01T00:00:00Z", "lastModEndDate": "2026-01-02T00:00:00Z", "startIndex": 0, "resultsPerPage": 1},
                    sleep_fn=fake_sleep,
                )
        self.assertEqual(call_count["n"], 2)
        self.assertEqual(payload["vulnerabilities"][0]["cve"]["id"], "CVE-2026-1")
        # First retry honored Retry-After: 0 (capped at 0 seconds, not exponential)
        self.assertEqual(slept, [0.0])

    def test_retries_exhaust_and_raise(self) -> None:
        slept: list[float] = []

        def fake_urlopen(req, timeout):
            raise HTTPError(req.full_url, 503, "down", {}, None)

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("aidefend_discovery.nvd_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                with self.assertRaises(HTTPError):
                    fetch_nvd_page(
                        {"lastModStartDate": "2026-01-01T00:00:00Z", "lastModEndDate": "2026-01-02T00:00:00Z", "startIndex": 0, "resultsPerPage": 1},
                        sleep_fn=slept.append,
                    )
        # NVD_MAX_RETRIES=5 → 5 sleeps before final attempt re-raises
        self.assertEqual(len(slept), 5)


if __name__ == "__main__":
    unittest.main()
