"""Small SQLite state helpers for connector cursors."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def init_state_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS connector_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_state_value(path: Path, key: str) -> str | None:
    init_state_db(path)
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT value FROM connector_state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row[0])
    finally:
        conn.close()


def set_state_value(path: Path, key: str, value: str) -> None:
    init_state_db(path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            INSERT INTO connector_state(key, value, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """,
            (key, value, now),
        )
        conn.commit()
    finally:
        conn.close()
