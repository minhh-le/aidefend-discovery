"""Tests for the local AIDEFEND Discovery review console backend."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from io import StringIO
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import export_review_digest
from aidefend_discovery import review_console

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestReviewConsoleBackend(unittest.TestCase):
    def load_session(self) -> review_console.ReportSession:
        return review_console.ReportSession.load(FIXTURES / "sample_gap_run.json")

    def test_import_report_uses_digest_scoring(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.coverage_score, export_review_digest.coverage_score(row.gap_report, row.coverage_ceiling))
        self.assertEqual(row.security_score, export_review_digest.security_score(row.candidate))
        self.assertEqual(row.recommended_action, "Promote")

    def test_candidate_identity_fallback_order(self) -> None:
        self.assertEqual(review_console.candidate_key({"content_hash": "abc", "source_id": "CVE-1"}), "content:abc")
        self.assertEqual(
            review_console.candidate_key({"source_type": "nvd_api", "source_id": "CVE-2026-1"}),
            "source:nvd_api:CVE-2026-1",
        )
        self.assertEqual(review_console.candidate_key({"id": "cand-1"}), "candidate:cand-1")
        self.assertTrue(review_console.candidate_key({"title": "Untitled"}, "report-a").startswith("generated:report-a:"))

    def test_reviewer_decision_persists_and_reloads(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "review.db"
            store = review_console.ReviewStore(db)
            saved = store.save(
                row,
                session.report_id,
                {
                    "review_decision": "promote",
                    "reviewer_notes": "Promote after checking nearest technique.",
                    "assigned_owner": "reviewer@example.test",
                    "confidence": "high",
                },
            )
            reloaded = review_console.ReviewStore(db).get(saved["candidate_key"])
        self.assertIsNotNone(reloaded)
        assert reloaded is not None
        self.assertEqual(reloaded["review_decision"], "promote")
        self.assertEqual(reloaded["reviewer_notes"], "Promote after checking nearest technique.")

    def test_backend_recommendation_and_reviewer_decision_are_separate(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            review = store.save(row, session.report_id, {"review_decision": "monitor"})
            detail = review_console.row_detail(row, session.report_id, review)
        self.assertEqual(detail["recommended_action"], "Promote")
        self.assertEqual(detail["review"]["review_decision"], "monitor")

    def test_reviewed_only_export_excludes_unreviewed_candidates(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(row, session.report_id, {"review_decision": "promote", "reviewer_notes": "Ready."})
            markdown = review_console.export_reviewed_markdown(session, store)
            csv_text = review_console.export_reviewed_csv(session, store)
        self.assertIn("Critical Model Loader Deserialization", markdown)
        self.assertNotIn("Known Prompt Injection Variant", markdown)
        rows = list(csv.DictReader(StringIO(csv_text)))
        self.assertEqual([r["candidate_id"] for r in rows], ["cand-promote"])

    def test_markdown_export_includes_decision_and_provenance(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-merge")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(
                row,
                session.report_id,
                {
                    "review_decision": "merge",
                    "merge_target": "AID-M-001",
                    "evidence_to_add": "CVE evidence should be linked.",
                },
            )
            markdown = review_console.export_reviewed_markdown(session, store)
        self.assertIn("- Backend recommended action: Merge Into Existing", markdown)
        self.assertIn("- Reviewer decision: Merge Into Existing", markdown)
        self.assertIn("- Source: nvd_api CVE-2026-0002", markdown)
        self.assertIn("- Raw score details: max_bm25=", markdown)

    def test_csv_export_includes_decision_and_provenance(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-needs-evidence")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(row, session.report_id, {"review_decision": "needs_evidence", "assigned_owner": "casey"})
            csv_text = review_console.export_reviewed_csv(session, store)
        rows = list(csv.DictReader(StringIO(csv_text)))
        self.assertEqual(rows[0]["review_decision"], "needs_evidence")
        self.assertEqual(rows[0]["assigned_owner"], "casey")
        self.assertEqual(rows[0]["backend_recommended_action"], "Needs Evidence")
        self.assertIn("max_bm25_below_threshold", rows[0]["gap_reason"])


if __name__ == "__main__":
    unittest.main()
