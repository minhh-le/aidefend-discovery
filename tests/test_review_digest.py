"""Tests for Markdown public review digest generation."""

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

import export_review_digest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestDigestScoring(unittest.TestCase):
    def test_coverage_score_caps_at_100(self) -> None:
        self.assertEqual(export_review_digest.coverage_score({"max_bm25": 25}, 10), 100)

    def test_coverage_score_handles_zero_or_missing_threshold(self) -> None:
        self.assertEqual(export_review_digest.coverage_score({"max_bm25": 5}, 0), 0)
        self.assertEqual(export_review_digest.coverage_score({"max_bm25": 5}, None), 0)

    def test_security_score_severity_bases(self) -> None:
        self.assertEqual(export_review_digest.security_score({"severity": "critical"}), 100)
        self.assertEqual(export_review_digest.security_score({"severity": "high"}), 85)
        self.assertEqual(export_review_digest.security_score({"severity": "medium"}), 60)
        self.assertEqual(export_review_digest.security_score({"severity": "low"}), 35)
        self.assertEqual(export_review_digest.security_score({}), 40)

    def test_security_score_evidence_boosts_cap_at_100(self) -> None:
        candidate = {
            "source_type": "ghsa_api",
            "ghsa_severity": "critical",
            "entities": {
                "cves": ["CVE-2026-1"],
                "ghsas": ["ghsa-aaaa-bbbb-cccc"],
                "cwes": ["CWE-502"],
                "version_constraints": ["< 1.0"],
            },
            "ghsa_packages": ["pypi:pkg"],
        }
        self.assertEqual(export_review_digest.security_score(candidate), 100)


class TestDigestActionRecommendation(unittest.TestCase):
    def test_low_coverage_high_security_recommends_promote(self) -> None:
        candidate = {
            "source_type": "ghsa_api",
            "source_urls": ["https://github.com/advisories/GHSA-aaaa-bbbb-cccc"],
            "entities": {"cves": ["CVE-2026-1"], "ghsas": ["ghsa-aaaa-bbbb-cccc"], "cwes": []},
            "severity": "high",
        }
        gap = {"is_gap": True, "nearest_technique_ids": ["AID-H-1"]}
        self.assertEqual(export_review_digest.recommended_action(candidate, gap, 20, 95), "Promote")

    def test_high_coverage_high_security_recommends_merge(self) -> None:
        candidate = {
            "source_type": "nvd_api",
            "source_urls": ["https://nvd.nist.gov/vuln/detail/CVE-2026-1"],
            "entities": {"cves": ["CVE-2026-1"], "ghsas": [], "cwes": []},
            "severity": "high",
        }
        self.assertEqual(export_review_digest.recommended_action(candidate, {}, 80, 95), "Merge Into Existing")

    def test_missing_evidence_recommends_needs_evidence(self) -> None:
        candidate = {
            "source_urls": ["https://example.test/post"],
            "entities": {"cves": [], "ghsas": [], "cwes": []},
            "severity": "unknown",
        }
        self.assertEqual(export_review_digest.recommended_action(candidate, {}, 10, 40), "Needs Evidence")

    def test_low_urgency_relevant_item_recommends_monitor(self) -> None:
        candidate = {
            "source_type": "ghsa_api",
            "source_urls": ["https://github.com/advisories/GHSA-aaaa-bbbb-cccc"],
            "entities": {"cves": [], "ghsas": ["ghsa-aaaa-bbbb-cccc"], "cwes": []},
            "severity": "medium",
        }
        self.assertEqual(export_review_digest.recommended_action(candidate, {}, 50, 70), "Monitor")

    def test_out_of_scope_fixture_recommends_reject(self) -> None:
        candidate = {
            "status": "rejected",
            "rejected_reason": "out_of_scope",
            "source_urls": ["https://example.test"],
            "entities": {"cves": ["CVE-2026-1"], "ghsas": [], "cwes": []},
        }
        self.assertEqual(export_review_digest.recommended_action(candidate, {}, 10, 50), "Reject")


class TestDigestCli(unittest.TestCase):
    def test_renders_markdown_from_sample_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "digest.md"
            rc = export_review_digest.main(
                [
                    "--report",
                    str(FIXTURES / "sample_gap_run.json"),
                    "--output",
                    str(out),
                    "--top-n",
                    "3",
                ]
            )
            self.assertEqual(rc, 0)
            text = out.read_text(encoding="utf-8")
        self.assertIn("# AIDEFEND Discovery Public Review Digest", text)
        self.assertIn("## Run Summary", text)
        self.assertIn("## Lowest Coverage Candidates", text)
        self.assertIn("## Highest Severity Candidates", text)
        self.assertIn("## Candidate Briefs", text)
        self.assertIn("## Methodology / Provenance Appendix", text)

    def test_respects_top_n_and_includes_summary_counts(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=2,
            generated_at="2026-05-05T00:00:00Z",
        )
        self.assertIn("- Candidates analyzed: 5", text)
        self.assertIn("- Candidates shown in detail: 2", text)
        self.assertIn("- Number in lowest coverage view: 2", text)
        self.assertIn("- Number in highest severity view: 2", text)

    def test_includes_both_top_level_tables(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=2,
            generated_at="2026-05-05T00:00:00Z",
        )
        self.assertIn("| Rank | Candidate | Coverage Score | Security Score | Recommended Action |", text)
        self.assertIn("| Rank | Candidate | Security Score | Coverage Score | Recommended Action |", text)

    def test_uses_report_timestamp_by_default_for_determinism(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=2,
        )
        self.assertIn("- Generated timestamp: 2026-05-05T00:00:00Z", text)

    def test_deduplicates_candidate_briefs_across_views(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=5,
            generated_at="2026-05-05T00:00:00Z",
        )
        self.assertEqual(text.count("### Critical Model Loader Deserialization"), 1)
        self.assertIn("- Candidate ID: cand-promote", text)

    def test_sample_mode_writes_digest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "sample.md"
            rc = export_review_digest.main(["--sample", "--output", str(out), "--top-n", "2"])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
