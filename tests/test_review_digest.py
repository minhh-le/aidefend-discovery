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
    def test_coverage_score_relative_to_report_ceiling(self) -> None:
        self.assertEqual(export_review_digest.coverage_score({"max_bm25": 25}, 100), 25)

    def test_coverage_score_caps_at_100_when_above_ceiling(self) -> None:
        self.assertEqual(export_review_digest.coverage_score({"max_bm25": 25}, 10), 100)

    def test_coverage_score_handles_zero_or_missing_ceiling(self) -> None:
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

    def test_low_relative_coverage_without_gap_does_not_recommend_promote(self) -> None:
        candidate = {
            "source_type": "ghsa_api",
            "source_urls": ["https://github.com/advisories/GHSA-aaaa-bbbb-cccc"],
            "entities": {"cves": ["CVE-2026-1"], "ghsas": ["ghsa-aaaa-bbbb-cccc"], "cwes": ["CWE-78"]},
            "severity": "high",
        }
        gap = {"is_gap": False, "nearest_technique_ids": ["AID-H-1"]}
        self.assertEqual(export_review_digest.recommended_action(candidate, gap, 20, 95), "Monitor")

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


class TestDigestQualityLayer(unittest.TestCase):
    def test_sample_quality_summary_splits_review_ready_enrichment_and_low_signal(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        rows = export_review_digest.build_rows(payload)
        self.assertEqual(export_review_digest.quality_summary(rows)["review_ready"], 3)
        self.assertEqual(export_review_digest.quality_status(rows[0]), export_review_digest.QUALITY_REVIEW_READY)
        self.assertEqual(export_review_digest.quality_status(rows[3]), export_review_digest.QUALITY_NEEDS_ENRICHMENT)
        self.assertEqual(export_review_digest.quality_status(rows[4]), export_review_digest.QUALITY_LOW_SIGNAL)

    def test_review_ready_requires_human_attack_narrative(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        candidate = dict(payload["candidates"][0])
        candidate["summary"] = "Security Score includes deterministic boosts for source metadata."
        candidate.pop("narrative", None)
        row = export_review_digest.build_rows({"candidates": [candidate], "gap_reports": [payload["gap_reports"][0]]})[0]
        self.assertNotEqual(export_review_digest.quality_status(row), export_review_digest.QUALITY_REVIEW_READY)
        narrative = export_review_digest.narrative_sections(row)
        primary = " ".join(narrative.values())
        self.assertNotIn("max_bm25", primary)

    def test_curated_sample_uses_real_ghsa_nvd_style_evidence(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        evidence = json.dumps(payload)
        self.assertIn("GHSA-5gfj-64gh-mgmw", evidence)
        self.assertIn("CVE-2026-39981", evidence)
        self.assertIn("https://nvd.nist.gov/vuln/detail/CVE-2026-39981", evidence)
        self.assertNotIn("GHSA-aaaa", evidence)
        self.assertNotIn("example.test", evidence)


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
        self.assertIn("- Review-ready candidates: 3", text)
        self.assertIn("- Needs enrichment: 1", text)
        self.assertIn("- Low signal: 1", text)
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

    def test_lowest_coverage_preserves_relative_order_above_threshold(self) -> None:
        payload = {
            "generated_at": "2026-05-05T00:00:00Z",
            "params": {"gap_bm25_max": 8.0},
            "candidates": [
                {"id": "low", "title": "Lower Match", "source_urls": ["https://example.test/low"], "entities": {"cves": ["CVE-1"]}},
                {"id": "high", "title": "Higher Match", "source_urls": ["https://example.test/high"], "entities": {"cves": ["CVE-2"]}},
            ],
            "gap_reports": [
                {"candidate_id": "low", "max_bm25": 10.0, "is_gap": False},
                {"candidate_id": "high", "max_bm25": 100.0, "is_gap": False},
            ],
        }
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=2,
            generated_at="2026-05-05T00:00:00Z",
        )
        self.assertIn("| 1 | Lower Match | 10/100 |", text)
        self.assertIn("| 2 | Higher Match | 100/100 |", text)

    def test_uses_report_timestamp_by_default_for_determinism(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=2,
        )
        self.assertIn("- Generated timestamp: 2026-05-08T00:00:00Z", text)

    def test_deduplicates_candidate_briefs_across_views(self) -> None:
        payload = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        text = export_review_digest.render_digest(
            payload,
            input_report=FIXTURES / "sample_gap_run.json",
            top_n=5,
            generated_at="2026-05-05T00:00:00Z",
        )
        self.assertEqual(text.count("### AGiXT Path Traversal in safe_join()"), 1)
        self.assertIn("- Candidate ID: cand-promote", text)
        self.assertNotIn("### langchain-mistralai==1.1.4", text)
        self.assertNotIn("Severity basis:", text)
        self.assertNotIn("Security Score includes deterministic boosts", text)

    def test_sample_mode_writes_digest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "sample.md"
            rc = export_review_digest.main(["--sample", "--output", str(out), "--top-n", "2"])
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
