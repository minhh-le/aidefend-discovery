"""Tests for the local AIDEFEND Discovery review console backend."""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from io import StringIO
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(export_review_digest.quality_status(row), export_review_digest.QUALITY_REVIEW_READY)

    def test_quality_layer_classifies_review_ready_enrichment_and_low_signal(self) -> None:
        session = self.load_session()
        statuses = {
            row.candidate_id: export_review_digest.quality_status(row)
            for row in session.rows
        }
        self.assertEqual(statuses["cand-promote"], export_review_digest.QUALITY_REVIEW_READY)
        self.assertEqual(statuses["cand-merge"], export_review_digest.QUALITY_REVIEW_READY)
        self.assertEqual(statuses["cand-monitor"], export_review_digest.QUALITY_REVIEW_READY)
        self.assertEqual(statuses["cand-needs-enrichment"], export_review_digest.QUALITY_NEEDS_ENRICHMENT)
        self.assertEqual(statuses["cand-low-signal"], export_review_digest.QUALITY_LOW_SIGNAL)
        self.assertEqual(review_console.run_quality_summary(session)["review_ready"], 3)
        self.assertEqual(review_console.run_quality_summary(session)["needs_enrichment"], 1)
        self.assertEqual(review_console.run_quality_summary(session)["low_signal"], 1)

    def test_curated_sample_uses_real_advisory_style_evidence(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        urls = row.candidate["source_urls"]
        self.assertIn("https://github.com/Josh-XT/AGiXT/security/advisories/GHSA-5gfj-64gh-mgmw", urls)
        self.assertIn("https://nvd.nist.gov/vuln/detail/CVE-2026-39981", urls)
        self.assertEqual(row.candidate["source_id"], "GHSA-5gfj-64gh-mgmw")
        self.assertEqual(row.candidate["entities"]["cves"], ["CVE-2026-39981"])
        self.assertNotIn("GHSA-aaaa", json.dumps(session.payload))
        self.assertNotIn("example.test", json.dumps(session.payload))

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

    def test_reviewed_count_is_scoped_to_current_session_rows(self) -> None:
        session = self.load_session()
        first = session.find_row("cand-promote")
        second = session.find_row("cand-merge")
        assert first is not None
        assert second is not None
        current_session = review_console.ReportSession(
            report_path=session.report_path,
            payload=session.payload,
            rows=[first],
            report_id=session.report_id,
        )
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(first, session.report_id, {"review_decision": "promote"})
            store.save(second, session.report_id, {"review_decision": "merge"})
            scoped_count = review_console.reviewed_count_for_session(current_session, store)
        self.assertEqual(scoped_count, 1)

    def test_reviewed_only_export_excludes_unreviewed_candidates(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(row, session.report_id, {"review_decision": "promote", "reviewer_notes": "Ready."})
            markdown = review_console.export_reviewed_markdown(session, store)
            csv_text = review_console.export_reviewed_csv(session, store)
        self.assertIn("AGiXT Path Traversal in safe_join()", markdown)
        self.assertNotIn("mcp-from-openapi SSRF", markdown)
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
        self.assertIn("- Source: ghsa_api GHSA-v6ph-xcq9-qxxj", markdown)
        self.assertIn("- Raw score details: max_bm25=", markdown)

    def test_csv_export_includes_decision_and_provenance(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-needs-enrichment")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(row, session.report_id, {"review_decision": "needs_evidence", "assigned_owner": "casey"})
            csv_text = review_console.export_reviewed_csv(session, store)
        rows = list(csv.DictReader(StringIO(csv_text)))
        self.assertEqual(rows[0]["review_decision"], "needs_evidence")
        self.assertEqual(rows[0]["assigned_owner"], "casey")
        self.assertEqual(rows[0]["backend_recommended_action"], "Monitor")
        self.assertIn("max_bm25_below_threshold", rows[0]["gap_reason"])

    def test_candidate_csv_export_includes_unreviewed_rows(self) -> None:
        session = self.load_session()
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            csv_text = review_console.export_candidates_csv(session, store)
        rows = list(csv.DictReader(StringIO(csv_text)))
        self.assertEqual(len(rows), 5)
        self.assertIn("AGiXT Path Traversal in safe_join()", {row["title"] for row in rows})
        self.assertEqual(
            {row["candidate_id"]: row["quality_status"] for row in rows}["cand-low-signal"],
            export_review_digest.QUALITY_LOW_SIGNAL,
        )

    def test_action_packet_keeps_candidate_boundary_and_playbook_fields(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            store.save(
                row,
                session.report_id,
                {
                    "review_decision": "promote",
                    "confidence": "high",
                    "reviewer_notes": "Candidate should be reviewed for a new harden entry.",
                },
            )
            packet = review_console.export_action_packet(session, store, "cand-promote")
        self.assertIn("Candidate-only maintainer packet", packet)
        self.assertIn("Discovery promotion: AGiXT Path Traversal in safe_join()", packet)
        self.assertIn("nearest_technique_ids", packet)
        self.assertIn("Human review required", packet)

    def test_shape_a_action_packet_uses_framework_item_placeholder(self) -> None:
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
                    "confidence": "high",
                    "merge_target": "AID-M-001",
                },
            )
            packet = review_console.export_action_packet(session, store, "cand-merge")
        self.assertIn("<verbatim upstream framework item>", packet)
        self.assertNotIn('items: ["mcp-from-openapi SSRF via untrusted OpenAPI $ref"]', packet)

    def test_ai_summary_without_key_falls_back_to_deterministic_summary(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            detail = review_console.row_detail(row, session.report_id, None)
            with patch.dict(
                os.environ,
                {"AI_SUMMARY_API_KEY": "", "AI_SUMMARY_MODEL": "", "AI_SUMMARY_BASE_URL": ""},
                clear=False,
            ):
                result = review_console.ai_summary(detail, {"api_key": "", "model": "", "base_url": ""})
        self.assertEqual(result["status"], "unavailable")
        self.assertTrue(result["fallback_used"])
        self.assertIn("What happened:", result["summary"])
        self.assertNotIn("max_bm25_below_threshold", result["summary"])
        self.assertIn("Likely gap", result["summary"])

    def test_default_queue_excludes_needs_enrichment_and_low_signal_noise(self) -> None:
        session = self.load_session()
        with tempfile.TemporaryDirectory() as td:
            store = review_console.ReviewStore(Path(td) / "review.db")
            rows = review_console.filtered_rows(session, store, {"tab": ["review_ready"]})
            low_signal = review_console.filtered_rows(session, store, {"tab": ["low_signal"]})
        self.assertEqual({row["candidate_id"] for row in rows}, {"cand-promote", "cand-merge", "cand-monitor"})
        self.assertEqual([row["candidate_id"] for row in low_signal], ["cand-low-signal"])
        self.assertNotIn("langchain-mistralai==1.1.4", {row["title"] for row in rows})

    def test_detail_narrative_leads_with_attacker_impact_not_score_mechanics(self) -> None:
        session = self.load_session()
        row = session.find_row("cand-promote")
        assert row is not None
        detail = review_console.row_detail(row, session.report_id, None)
        sections = detail["sections"]
        self.assertIn("attacker", sections["why_it_matters"].lower())
        self.assertIn("Likely gap", sections["gap_assessment"])
        primary_text = " ".join(
            [
                sections["what_happened"],
                sections["why_it_matters"],
                sections["existing_coverage"],
                sections["gap_assessment"],
            ]
        )
        self.assertNotIn("Severity basis", primary_text)
        self.assertNotIn("Security Score includes deterministic boosts", primary_text)
        self.assertIn("max_bm25", sections["provenance"]["raw_score_details"])

    def test_live_advisory_scan_with_too_few_review_ready_adds_curated_guidance(self) -> None:
        fixture = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        ghsa_candidate = deepcopy(fixture["candidates"][0])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(review_console, "ingest_ghsa_incremental", return_value=[ghsa_candidate]), patch.object(
                review_console, "ingest_nvd_incremental", return_value=[]
            ), patch.object(
                review_console, "DEFAULT_CANDIDATES_OUT", root / "candidates.jsonl"
            ):
                report_path = review_console.run_discovery_preset(
                    "live_advisory_scan",
                    {"max_items": 1, "fetch_pages": False},
                    lambda _msg: None,
                    lambda _msg: None,
                    lambda **_kwargs: None,
                    reports_dir=root,
                    state_db=root / "state.db",
                )
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["quality_summary"]["review_ready"], 1)
        self.assertEqual(payload["quality_guidance"]["level"], "curated_demo_recommended")
        self.assertIn("fewer than 3 review-ready", payload["quality_guidance"]["message"])

    def test_source_health_reports_optional_key_states(self) -> None:
        health = review_console.source_health()
        self.assertIn(health["rss"]["status"], {"available", "unavailable"})
        self.assertIn(health["nvd"]["status"], {"anonymous", "key_configured"})
        self.assertIn(health["ghsa"]["status"], {"anonymous", "key_configured"})
        self.assertIn(health["ai"]["status"], {"enabled", "unavailable"})

    def test_full_sweep_merges_sources_into_one_report(self) -> None:
        fixture = json.loads((FIXTURES / "sample_gap_run.json").read_text(encoding="utf-8"))
        rss_candidate = deepcopy(fixture["candidates"][3])
        nvd_candidate = deepcopy(fixture["candidates"][1])
        ghsa_candidate = deepcopy(fixture["candidates"][0])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(review_console, "_ingest_rss", return_value=[rss_candidate]), patch.object(
                review_console, "ingest_nvd_incremental", return_value=[nvd_candidate]
            ), patch.object(
                review_console, "ingest_ghsa_incremental", return_value=[ghsa_candidate]
            ), patch.object(
                review_console, "DEFAULT_CANDIDATES_OUT", root / "candidates.jsonl"
            ):
                report_path = review_console.run_discovery_preset(
                    "full_sweep",
                    {"max_items": 1, "fetch_pages": False},
                    lambda _msg: None,
                    lambda _msg: None,
                    lambda **_kwargs: None,
                    reports_dir=root,
                    state_db=root / "state.db",
                )
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["source"], "broad_source_sweep")
        self.assertEqual(payload["sources"], ["ghsa", "nvd", "rss"])
        self.assertEqual(len(payload["candidates"]), 3)


if __name__ == "__main__":
    unittest.main()
