from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from aidefend_discovery.state_store import (
    candidate_counts,
    get_state_value,
    init_full_schema,
    init_state_db,
    iter_export_rows,
    list_candidates,
    record_gap_report,
    record_run,
    seen_in_window,
    set_state_value,
    upsert_candidate,
)


class TestStateStore(unittest.TestCase):
    def test_init_creates_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "state.db"
            init_state_db(db_path)
            conn = sqlite3.connect(db_path)
            try:
                row = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='connector_state'"
                ).fetchone()
                self.assertIsNotNone(row)
            finally:
                conn.close()

    def test_set_and_get_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "state.db"
            init_state_db(db_path)
            set_state_value(db_path, "nvd_lastmod_end", "2026-05-01T00:00:00Z")
            self.assertEqual(get_state_value(db_path, "nvd_lastmod_end"), "2026-05-01T00:00:00Z")

    def test_preserves_previous_value_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "state.db"
            init_state_db(db_path)
            set_state_value(db_path, "nvd_lastmod_end", "2026-05-01T00:00:00Z")
            try:
                raise RuntimeError("ingest failed")
            except RuntimeError:
                pass
            self.assertEqual(get_state_value(db_path, "nvd_lastmod_end"), "2026-05-01T00:00:00Z")


def _sample_candidate(content_hash: str = "abc123", cid: str = "candidate-test-1") -> dict:
    return {
        "id": cid,
        "status": "candidate",
        "title": "Sample candidate",
        "summary": "A test candidate",
        "source_urls": ["https://example.test/x"],
        "retrieved_at": "2026-05-02T12:00:00Z",
        "license_note": "test",
        "confidence": 0.5,
        "content_hash": content_hash,
        "raw_hash": content_hash,
        "feed_url": "test_feed",
        "source_type": "rss",
        "source_id": cid,
        "entities": {"cves": [], "ghsas": [], "cwes": [], "version_constraints": []},
    }


def _sample_gap_report(candidate_id: str, *, max_bm25: float = 5.0, is_gap: bool = False) -> dict:
    return {
        "candidate_id": candidate_id,
        "nearest_technique_ids": ["AID-H-001"],
        "bm25_scores": [max_bm25],
        "max_bm25": max_bm25,
        "threat_id_overlap": [],
        "candidate_threat_tokens": [],
        "is_gap": is_gap,
        "gap_reason": "test",
        "suggested_tactic_ids": ["harden"],
        "suggested_pillars": ["model"],
        "suggested_phases": ["building"],
        "rationale": "test",
        "nearest_lexical_overlap_terms": [["alpha", "bravo"]],
        "bridge_rationales": ["CWE-94 → AID-H-001 (test)"],
    }


class TestFullSchema(unittest.TestCase):
    def test_init_full_schema_creates_v1_tables(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "s.db"
            init_full_schema(db)
            conn = sqlite3.connect(db)
            try:
                names = {
                    row[0]
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                }
                self.assertEqual(
                    names,
                    {"connector_state", "runs", "candidates", "gap_reports", "seen_window"},
                )
                v = conn.execute("PRAGMA user_version").fetchone()[0]
                self.assertEqual(v, 1)
            finally:
                conn.close()

    def test_idempotent_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "s.db"
            run_id = record_run(db, source="test", params={"x": 1})
            inserted_first = upsert_candidate(db, _sample_candidate(), run_id=run_id)
            inserted_second = upsert_candidate(db, _sample_candidate(), run_id=run_id)
            self.assertTrue(inserted_first)
            self.assertFalse(inserted_second)
            counts = candidate_counts(db)
            self.assertEqual(counts["total"], 1)

    def test_record_gap_report_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "s.db"
            run_id = record_run(db, source="test", params={})
            cand = _sample_candidate()
            upsert_candidate(db, cand, run_id=run_id)
            record_gap_report(db, run_id=run_id, gap_report=_sample_gap_report(cand["id"]))
            rows = list_candidates(db)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["gap_report"]["bridge_rationales"], ["CWE-94 → AID-H-001 (test)"])

    def test_seen_in_window_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "s.db"
            self.assertFalse(seen_in_window(db, feed_url="f", entry_id="e1", window_key="20260502"))
            self.assertTrue(seen_in_window(db, feed_url="f", entry_id="e1", window_key="20260502"))
            # different window key → still considered new
            self.assertFalse(seen_in_window(db, feed_url="f", entry_id="e1", window_key="20260503"))

    def test_iter_export_rows_emits_columns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "s.db"
            run_id = record_run(db, source="test", params={})
            cand = _sample_candidate()
            upsert_candidate(db, cand, run_id=run_id)
            record_gap_report(db, run_id=run_id, gap_report=_sample_gap_report(cand["id"], is_gap=True))
            rows = list(iter_export_rows(db))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["candidate_id"], cand["id"])
            self.assertEqual(rows[0]["is_gap"], 1)
            self.assertIn("CWE-94", rows[0]["bridge_rationales"])
            self.assertEqual(rows[0]["source_urls"], "https://example.test/x")


if __name__ == "__main__":
    unittest.main()
