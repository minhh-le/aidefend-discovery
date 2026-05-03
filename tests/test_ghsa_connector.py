from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from aidefend_discovery.ghsa_ingest import (
    GHSA_API_URL,
    build_ghsa_query,
    fetch_ghsa_page,
    ghsa_to_candidate,
    ingest_ghsa_incremental,
    _next_url,
)


_SAMPLE_ADVISORY = {
    "ghsa_id": "GHSA-abcd-efgh-ijkl",
    "cve_id": "CVE-2026-9999",
    "html_url": "https://github.com/advisories/GHSA-abcd-efgh-ijkl",
    "summary": "Prompt injection via crafted user input",
    "description": "An attacker can craft input that causes the LLM to disclose system prompt content.",
    "type": "reviewed",
    "severity": "high",
    "vulnerabilities": [
        {
            "package": {"ecosystem": "pip", "name": "langchain"},
            "vulnerable_version_range": "< 0.1.5",
            "patched_versions": ["0.1.5"],
        }
    ],
    "cwes": [{"cwe_id": "CWE-94", "name": "Code Injection"}, {"cwe_id": "CWE-200", "name": "Information Exposure"}],
    "published_at": "2026-04-15T00:00:00Z",
    "updated_at": "2026-04-20T00:00:00Z",
    "withdrawn_at": None,
    "references": [
        "https://github.com/langchain-ai/langchain/security/advisories/GHSA-abcd-efgh-ijkl",
        "https://nvd.nist.gov/vuln/detail/CVE-2026-9999",
    ],
}


class TestGhsaQuery(unittest.TestCase):
    def test_build_query_default_shape(self) -> None:
        q = build_ghsa_query(updated_after="2026-04-01T00:00:00Z")
        self.assertEqual(q["type"], "reviewed")
        self.assertEqual(q["sort"], "updated")
        self.assertEqual(q["direction"], "asc")
        self.assertEqual(q["per_page"], "100")
        self.assertEqual(q["updated"], ">2026-04-01T00:00:00Z")

    def test_build_query_caps_per_page(self) -> None:
        q = build_ghsa_query(per_page=999)
        self.assertEqual(q["per_page"], "100")

    def test_next_url_parses_link_header(self) -> None:
        link = (
            '<https://api.github.com/advisories?after=Y3Vyc29yOnYyOpHOAYpUgQ%3D%3D&per_page=100>; rel="next", '
            '<https://api.github.com/advisories?after=zzz>; rel="last"'
        )
        self.assertIn("after=", _next_url(link) or "")
        self.assertIsNone(_next_url(None))


class TestGhsaParsing(unittest.TestCase):
    def test_normalize_advisory(self) -> None:
        c = ghsa_to_candidate(_SAMPLE_ADVISORY)
        self.assertEqual(c["status"], "candidate")
        self.assertEqual(c["source_type"], "ghsa_api")
        self.assertEqual(c["source_id"], "GHSA-abcd-efgh-ijkl")
        self.assertIn("CVE-2026-9999", c["entities"]["cves"])
        self.assertIn("ghsa-abcd-efgh-ijkl", c["entities"]["ghsas"])
        self.assertIn("CWE-94", c["entities"]["cwes"])
        self.assertIn("CWE-200", c["entities"]["cwes"])
        self.assertIn("vulnerable:< 0.1.5", c["entities"]["version_constraints"])
        self.assertIn("patched:0.1.5", c["entities"]["version_constraints"])
        self.assertIn("pip:langchain", c["ghsa_packages"])
        self.assertEqual(c["ghsa_severity"], "high")
        # html_url leads source_urls; references appended
        self.assertEqual(c["source_urls"][0], "https://github.com/advisories/GHSA-abcd-efgh-ijkl")
        # Title falls back to GHSA id
        self.assertEqual(c["title"], "GHSA-abcd-efgh-ijkl")

    def test_advisory_without_cve(self) -> None:
        adv = dict(_SAMPLE_ADVISORY)
        adv["cve_id"] = None
        c = ghsa_to_candidate(adv)
        self.assertEqual(c["entities"]["cves"], [])

    def test_dedupes_references(self) -> None:
        adv = dict(_SAMPLE_ADVISORY)
        adv["references"] = [
            "https://example.test/x",
            "https://example.test/x",
            {"url": "https://example.test/y"},
        ]
        c = ghsa_to_candidate(adv)
        self.assertEqual(c["source_urls"].count("https://example.test/x"), 1)


class TestGhsaFetch(unittest.TestCase):
    def _stub_response(self, payload: bytes, link: str | None = None):
        m = mock.MagicMock()
        m.read.return_value = payload
        m.headers.get = lambda k, default=None: {"Link": link}.get(k, default) if link else default
        m.__enter__.return_value = m
        m.__exit__.return_value = False
        return m

    def test_auth_header_set_when_token_present(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            captured["url"] = req.full_url
            return self._stub_response(b"[]")

        with mock.patch.dict("os.environ", {"GH_PAT_FOR_GHSA": "ghp_test"}, clear=False):
            with mock.patch("aidefend_discovery.ghsa_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                items, next_url = fetch_ghsa_page(build_ghsa_query(updated_after="2026-01-01T00:00:00Z"))
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer ghp_test")
        self.assertTrue(captured["url"].startswith(GHSA_API_URL))
        self.assertEqual(items, [])
        self.assertIsNone(next_url)

    def test_falls_back_to_github_token(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout):
            captured["headers"] = dict(req.headers)
            return self._stub_response(b"[]")

        env = {k: v for k, v in __import__("os").environ.items() if k not in ("GH_PAT_FOR_GHSA", "GITHUB_TOKEN")}
        env["GITHUB_TOKEN"] = "ghp_fallback"
        with mock.patch.dict("os.environ", env, clear=True):
            with mock.patch("aidefend_discovery.ghsa_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                fetch_ghsa_page(build_ghsa_query())
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer ghp_fallback")

    def test_retries_on_403_then_succeeds(self) -> None:
        slept: list[float] = []
        n = {"i": 0}

        def fake_urlopen(req, timeout):
            n["i"] += 1
            if n["i"] == 1:
                raise HTTPError(req.full_url, 403, "rate", {"Retry-After": "0"}, None)
            return self._stub_response(b"[]")

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch("aidefend_discovery.ghsa_ingest.urllib.request.urlopen", side_effect=fake_urlopen):
                fetch_ghsa_page(build_ghsa_query(), sleep_fn=slept.append)
        self.assertEqual(n["i"], 2)
        self.assertEqual(slept, [0.0])


class TestGhsaIncrementalCursor(unittest.TestCase):
    def test_walks_pages_until_no_next(self) -> None:
        page1 = ([dict(_SAMPLE_ADVISORY, ghsa_id=f"GHSA-page1-{i:04x}-aaaa") for i in range(2)], "https://api.github.com/advisories?after=AAA")
        page2 = ([dict(_SAMPLE_ADVISORY, ghsa_id=f"GHSA-page2-{i:04x}-aaaa") for i in range(2)], None)
        calls = {"i": 0}

        def fake_fetch(target, timeout):
            calls["i"] += 1
            return page1 if calls["i"] == 1 else page2

        out = ingest_ghsa_incremental(
            updated_after="2026-01-01T00:00:00Z",
            max_pages=5,
            fetch_page_fn=fake_fetch,
        )
        self.assertEqual(len(out), 4)
        self.assertEqual(calls["i"], 2)
        self.assertEqual(out[0]["source_type"], "ghsa_api")


if __name__ == "__main__":
    unittest.main()
