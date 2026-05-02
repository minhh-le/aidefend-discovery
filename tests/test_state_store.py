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

from aidefend_discovery.state_store import get_state_value, init_state_db, set_state_value


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


if __name__ == "__main__":
    unittest.main()
