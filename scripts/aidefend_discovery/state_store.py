"""SQLite state for connector cursors, candidates, runs, gap reports, and idempotency.

Schema versioning via `PRAGMA user_version`:
  v0 (legacy): only `connector_state` table.
  v1 (this module): adds `runs`, `candidates`, `gap_reports`, `seen_window`.

`init_full_schema(path)` is idempotent and safe to call repeatedly. Connector
cursor APIs (`get_state_value` / `set_state_value`) keep their original
contract so existing callers don't break.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_state_db(path: Path) -> None:
    """Idempotent legacy initializer; only ensures `connector_state` exists.

    Kept so existing callers (NVD cursor flow) keep working unchanged. The
    full schema migration runs lazily via `init_full_schema`.
    """
    conn = _connect(path)
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


def init_full_schema(path: Path) -> None:
    """Create v1 schema (runs, candidates, gap_reports, seen_window)."""
    init_state_db(path)
    conn = _connect(path)
    try:
        cur = conn.execute("PRAGMA user_version")
        version = int(cur.fetchone()[0])
        if version >= SCHEMA_VERSION:
            return
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generated_at TEXT NOT NULL,
                source TEXT NOT NULL,
                params TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS candidates (
                content_hash TEXT PRIMARY KEY,
                id TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL,
                source_type TEXT,
                source_id TEXT,
                feed_url TEXT,
                retrieved_at TEXT NOT NULL,
                payload TEXT NOT NULL,
                first_seen_run INTEGER REFERENCES runs(id),
                last_seen_run INTEGER REFERENCES runs(id),
                promoted_pr_url TEXT,
                rejected_reason TEXT,
                review_updated_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);
            CREATE INDEX IF NOT EXISTS idx_candidates_source_id ON candidates(source_type, source_id);
            CREATE TABLE IF NOT EXISTS gap_reports (
                run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                candidate_id TEXT NOT NULL,
                max_bm25 REAL,
                is_gap INTEGER NOT NULL,
                gap_reason TEXT,
                payload TEXT NOT NULL,
                PRIMARY KEY (run_id, candidate_id)
            );
            CREATE INDEX IF NOT EXISTS idx_gap_reports_candidate ON gap_reports(candidate_id);
            CREATE TABLE IF NOT EXISTS seen_window (
                feed_url TEXT NOT NULL,
                entry_id TEXT NOT NULL,
                window_key TEXT NOT NULL,
                seen_at TEXT NOT NULL,
                PRIMARY KEY (feed_url, entry_id, window_key)
            );
            """
        )
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    finally:
        conn.close()


# ---------- legacy connector-cursor API (unchanged contract) ----------


def get_state_value(path: Path, key: str) -> str | None:
    init_state_db(path)
    conn = _connect(path)
    try:
        row = conn.execute("SELECT value FROM connector_state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return str(row[0])
    finally:
        conn.close()


def set_state_value(path: Path, key: str, value: str) -> None:
    init_state_db(path)
    now = _now_iso()
    conn = _connect(path)
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


# ---------- v1 store: runs, candidates, gap_reports, idempotency ----------


def record_run(path: Path, *, source: str, params: dict[str, Any]) -> int:
    """Insert a new run row; return its run_id."""
    init_full_schema(path)
    conn = _connect(path)
    try:
        cur = conn.execute(
            "INSERT INTO runs(generated_at, source, params) VALUES (?, ?, ?)",
            (_now_iso(), source, json.dumps(params, sort_keys=True)),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def upsert_candidate(path: Path, candidate: dict[str, Any], *, run_id: int) -> bool:
    """Insert a candidate keyed by content_hash; return True if new, False if seen.

    Existing rows have their `last_seen_run` updated and `payload` refreshed
    only if the new payload's `retrieved_at` is newer (idempotent and
    monotonic). Status / review fields are NEVER overwritten by ingest.
    """
    init_full_schema(path)
    content_hash = str(candidate.get("content_hash") or candidate.get("raw_hash") or "")
    if not content_hash:
        raise ValueError("candidate must have content_hash or raw_hash")
    cand_id = str(candidate["id"])
    payload = json.dumps(candidate, sort_keys=True)
    conn = _connect(path)
    try:
        existing = conn.execute(
            "SELECT retrieved_at FROM candidates WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO candidates(
                    content_hash, id, status, source_type, source_id, feed_url,
                    retrieved_at, payload, first_seen_run, last_seen_run
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    content_hash,
                    cand_id,
                    str(candidate.get("status", "candidate")),
                    candidate.get("source_type"),
                    candidate.get("source_id"),
                    candidate.get("feed_url"),
                    str(candidate.get("retrieved_at") or _now_iso()),
                    payload,
                    run_id,
                    run_id,
                ),
            )
            conn.commit()
            return True
        # Existing row: update last_seen_run + payload if newer.
        new_retrieved_at = str(candidate.get("retrieved_at") or "")
        prior_retrieved_at = str(existing[0] or "")
        if new_retrieved_at and new_retrieved_at >= prior_retrieved_at:
            conn.execute(
                """
                UPDATE candidates
                SET last_seen_run = ?, retrieved_at = ?, payload = ?
                WHERE content_hash = ?
                """,
                (run_id, new_retrieved_at, payload, content_hash),
            )
        else:
            conn.execute(
                "UPDATE candidates SET last_seen_run = ? WHERE content_hash = ?",
                (run_id, content_hash),
            )
        conn.commit()
        return False
    finally:
        conn.close()


def record_gap_report(path: Path, *, run_id: int, gap_report: dict[str, Any]) -> None:
    init_full_schema(path)
    candidate_id = str(gap_report["candidate_id"])
    conn = _connect(path)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO gap_reports(
                run_id, candidate_id, max_bm25, is_gap, gap_reason, payload
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                candidate_id,
                float(gap_report.get("max_bm25") or 0.0),
                1 if gap_report.get("is_gap") else 0,
                gap_report.get("gap_reason"),
                json.dumps(gap_report, sort_keys=True),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def seen_in_window(path: Path, *, feed_url: str, entry_id: str, window_key: str) -> bool:
    """Return True if (feed_url, entry_id, window_key) was already recorded; insert otherwise.

    `window_key` is typically a YYYYMMDD or YYYYMM string so the same item
    seen on different days/windows still counts as new for that window.
    """
    init_full_schema(path)
    conn = _connect(path)
    try:
        row = conn.execute(
            "SELECT 1 FROM seen_window WHERE feed_url = ? AND entry_id = ? AND window_key = ?",
            (feed_url, entry_id, window_key),
        ).fetchone()
        if row is not None:
            return True
        conn.execute(
            "INSERT INTO seen_window(feed_url, entry_id, window_key, seen_at) VALUES (?, ?, ?, ?)",
            (feed_url, entry_id, window_key, _now_iso()),
        )
        conn.commit()
        return False
    finally:
        conn.close()


# ---------- read APIs (used by export, metrics, MCP) ----------


def list_candidates(
    path: Path,
    *,
    status: str | None = None,
    source_type: str | None = None,
    is_gap: bool | None = None,
    keyword: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Read candidates with optional filters; results join the latest gap report."""
    init_full_schema(path)
    where: list[str] = []
    args: list[Any] = []
    if status:
        where.append("c.status = ?")
        args.append(status)
    if source_type:
        where.append("c.source_type = ?")
        args.append(source_type)
    if keyword:
        where.append("(c.id LIKE ? OR c.payload LIKE ?)")
        args.extend([f"%{keyword}%", f"%{keyword}%"])
    if is_gap is True:
        where.append("g.is_gap = 1")
    elif is_gap is False:
        where.append("g.is_gap = 0")
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT c.content_hash, c.id, c.status, c.source_type, c.source_id, c.feed_url,
               c.retrieved_at, c.payload, c.promoted_pr_url, c.rejected_reason,
               g.max_bm25, g.is_gap, g.gap_reason, g.payload AS gr_payload
        FROM candidates c
        LEFT JOIN (
            SELECT candidate_id, max_bm25, is_gap, gap_reason, payload,
                   ROW_NUMBER() OVER (PARTITION BY candidate_id ORDER BY run_id DESC) AS rn
            FROM gap_reports
        ) g ON g.candidate_id = c.id AND g.rn = 1
        {where_sql}
        ORDER BY c.retrieved_at DESC
        LIMIT ?
    """
    args.append(int(limit))
    conn = _connect(path)
    try:
        cols = [
            "content_hash", "id", "status", "source_type", "source_id", "feed_url",
            "retrieved_at", "payload", "promoted_pr_url", "rejected_reason",
            "max_bm25", "is_gap", "gap_reason", "gr_payload",
        ]
        rows = conn.execute(sql, args).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            d = dict(zip(cols, row))
            d["candidate"] = json.loads(d.pop("payload"))
            d["gap_report"] = json.loads(d.pop("gr_payload")) if d.get("gr_payload") else None
            d["is_gap"] = bool(d["is_gap"]) if d["is_gap"] is not None else None
            out.append(d)
        return out
    finally:
        conn.close()


def get_candidate(path: Path, candidate_id: str) -> dict[str, Any] | None:
    rows = list_candidates(path, keyword=candidate_id, limit=10)
    for r in rows:
        if r["id"] == candidate_id:
            return r
    return None


def candidate_counts(path: Path) -> dict[str, int]:
    """Aggregate counts for the metrics emitter."""
    init_full_schema(path)
    conn = _connect(path)
    try:
        out: dict[str, int] = {}
        out["total"] = int(conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0])
        for status in ("candidate", "rejected", "promoted"):
            out[f"status_{status}"] = int(
                conn.execute("SELECT COUNT(*) FROM candidates WHERE status = ?", (status,)).fetchone()[0]
            )
        out["total_runs"] = int(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
        out["total_gap_reports"] = int(conn.execute("SELECT COUNT(*) FROM gap_reports").fetchone()[0])
        out["is_gap_true"] = int(
            conn.execute("SELECT COUNT(DISTINCT candidate_id) FROM gap_reports WHERE is_gap = 1").fetchone()[0]
        )
        return out
    finally:
        conn.close()


def iter_export_rows(path: Path) -> Iterable[dict[str, Any]]:
    """Stream rows for CSV export. Joins each candidate with its latest gap report."""
    for row in list_candidates(path, limit=10**6):
        cand = row["candidate"]
        gr = row.get("gap_report") or {}
        yield {
            "candidate_id": row["id"],
            "status": row["status"],
            "source_type": row["source_type"] or "",
            "source_id": row["source_id"] or "",
            "feed_url": row["feed_url"] or "",
            "retrieved_at": row["retrieved_at"],
            "max_bm25": "" if row.get("max_bm25") is None else row["max_bm25"],
            "is_gap": "" if row.get("is_gap") is None else int(row["is_gap"]),
            "gap_reason": row.get("gap_reason") or "",
            "suggested_tactic_ids": ";".join(gr.get("suggested_tactic_ids") or []),
            "bridge_rationales": ";".join(gr.get("bridge_rationales") or []),
            "source_urls": ";".join(cand.get("source_urls") or []),
            "promoted_pr_url": row.get("promoted_pr_url") or "",
            "rejected_reason": row.get("rejected_reason") or "",
        }
