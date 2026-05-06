"""Read-only sqlite client for the aidefend-discovery candidate store.

The schema (runs / candidates / gap_reports / seen_window) is owned by the
aidefend-discovery repo's `scripts/aidefend_discovery/state_store.py`. We
mirror the read paths here so MCP discovery tools can serve queries without
depending on the discovery repo as a Python package.

Concurrency: sqlite handles concurrent readers fine. We open a fresh
connection per call to avoid stale state across requests.

Namespace wall: every dict returned by helpers in this module includes
`discovery_namespace: true` and any AID-* references are confined to a
`references_aid` sidecar list so downstream agents cannot blur the line
between candidate hypotheses and official AIDEFEND truth.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

DISCOVERY_DISCLAIMER = (
    "Hypothesis only; verify against AIDEFEND structured layer "
    "(query_aidefend / get_technique_detail) before treating as official."
)

_AID_RE = re.compile(r"\bAID-[A-Z]+(?:-\d+(?:\.\d+)?)?\b")


def is_discovery_configured() -> bool:
    """True iff DISCOVERY_DB_PATH is set and the file exists."""
    from app.config import settings

    p = settings.DISCOVERY_DB_PATH
    return bool(p) and Path(p).exists()


def discovery_namespace_response(
    *,
    configured: bool,
    payload: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Wrap any discovery-tool response with the namespace marker + disclaimer."""
    out: dict[str, Any] = {
        "discovery_namespace": True,
        "configured": configured,
        "disclaimer": DISCOVERY_DISCLAIMER,
    }
    if error:
        out["error"] = error
    if payload is not None:
        out.update(payload)
    return out


def _connect_readonly() -> sqlite3.Connection:
    from app.config import settings

    path = settings.DISCOVERY_DB_PATH
    if not path:
        raise RuntimeError("DISCOVERY_DB_PATH is not configured")
    # mode=ro requires URI; fall back to default if URI mode fails.
    uri = f"file:{Path(path).resolve()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _strip_aid_ids(s: str) -> tuple[str, list[str]]:
    """Pull AID-* IDs into a sidecar list and return (clean_text, ids)."""
    ids = sorted(set(_AID_RE.findall(s)))
    if not ids:
        return s, []
    clean = _AID_RE.sub("[AID-REDACTED]", s)
    return clean, ids


def _summarize_candidate(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a candidates+gap_reports JOIN row into a wall-safe summary."""
    cand = json.loads(row["payload"]) if row["payload"] else {}
    gr = json.loads(row["gr_payload"]) if row["gr_payload"] else None

    summary_text = str(cand.get("summary") or "")[:600]
    summary_clean, summary_aids = _strip_aid_ids(summary_text)
    title_clean, title_aids = _strip_aid_ids(str(cand.get("title") or ""))

    out: dict[str, Any] = {
        "candidate_id": row["id"],
        "status": row["status"],
        "source_type": row["source_type"],
        "source_id": row["source_id"],
        "feed_url": row["feed_url"],
        "retrieved_at": row["retrieved_at"],
        "title": title_clean,
        "summary": summary_clean,
        "source_urls": cand.get("source_urls") or [],
        "entities": cand.get("entities") or {},
    }
    if gr:
        out["max_bm25"] = gr.get("max_bm25")
        out["is_gap"] = bool(gr.get("is_gap"))
        out["gap_reason"] = gr.get("gap_reason")
        out["bridge_rationales"] = gr.get("bridge_rationales") or []
        # AID-* IDs from gap report go into the sidecar with the disclaimer.
        nearest = gr.get("nearest_technique_ids") or []
        suggested_tactics = gr.get("suggested_tactic_ids") or []
        if nearest or suggested_tactics or summary_aids or title_aids:
            out["references_aid"] = sorted(
                set(nearest)
                | set(summary_aids)
                | set(title_aids)
            )
            out["references_aid_note"] = DISCOVERY_DISCLAIMER
            out["suggested_tactic_hints"] = suggested_tactics
    return out


def list_candidates(
    *,
    keyword: str | None = None,
    source_type: str | None = None,
    is_gap: bool | None = None,
    status: str | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Read candidates + their latest gap report. Read-only."""
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
               c.retrieved_at, c.payload,
               g.payload AS gr_payload
        FROM candidates c
        LEFT JOIN (
            SELECT candidate_id, payload,
                   ROW_NUMBER() OVER (PARTITION BY candidate_id ORDER BY run_id DESC) AS rn
            FROM gap_reports
        ) g ON g.candidate_id = c.id AND g.rn = 1
        {where_sql}
        ORDER BY c.retrieved_at DESC
        LIMIT ?
    """
    args.append(int(top_k))
    conn = _connect_readonly()
    try:
        rows = conn.execute(sql, args).fetchall()
        return [_summarize_candidate(r) for r in rows]
    finally:
        conn.close()


def get_candidate_detail(candidate_id: str) -> dict[str, Any] | None:
    """Full candidate + latest gap report by id."""
    conn = _connect_readonly()
    try:
        row = conn.execute(
            """
            SELECT c.content_hash, c.id, c.status, c.source_type, c.source_id, c.feed_url,
                   c.retrieved_at, c.payload,
                   g.payload AS gr_payload
            FROM candidates c
            LEFT JOIN (
                SELECT candidate_id, payload,
                       ROW_NUMBER() OVER (PARTITION BY candidate_id ORDER BY run_id DESC) AS rn
                FROM gap_reports
            ) g ON g.candidate_id = c.id AND g.rn = 1
            WHERE c.id = ?
            """,
            (candidate_id,),
        ).fetchone()
        if row is None:
            return None
        summary = _summarize_candidate(row)
        gr_payload = json.loads(row["gr_payload"]) if row["gr_payload"] else None
        if gr_payload:
            summary["gap_report"] = gr_payload
        cand_payload = json.loads(row["payload"])
        summary["body_extracted"] = cand_payload.get("body_extracted")
        summary["retrieval_chunks"] = cand_payload.get("retrieval_chunks") or []
        return summary
    finally:
        conn.close()


def latest_anchor_diff_path() -> Path | None:
    """Locate the most recent anchor_diff_YYYYMMDD.json under the configured reports dir."""
    from app.config import settings

    reports_dir = settings.DISCOVERY_REPORTS_PATH
    if reports_dir is None and settings.DISCOVERY_DB_PATH:
        # Default heuristic: <db parent>/../../reports
        db_parent = Path(settings.DISCOVERY_DB_PATH).resolve().parent
        reports_dir = db_parent.parent.parent / "reports"
    if reports_dir is None:
        return None
    p = Path(reports_dir)
    if not p.exists():
        return None
    candidates = sorted(
        set(p.glob("anchor_diff_*.json")) | set(p.glob("auto/*/anchor_diff_*.json"))
    )
    return candidates[-1] if candidates else None
