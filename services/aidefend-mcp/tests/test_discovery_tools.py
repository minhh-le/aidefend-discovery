"""
Contract tests for the discovery-namespace MCP tools.

These assert the namespace wall holds: every response carries
discovery_namespace=True + a disclaimer; AID-* IDs are confined to a
references_aid sidecar; explain_candidate_mapping always returns at
least one source_url when the candidate is found.

The tests run against an in-memory sqlite store created here, so they
do not require the aidefend-discovery repo to be present.
"""

from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

# We need the settings to be set BEFORE the tools import the discovery store
# (which reads settings.DISCOVERY_DB_PATH lazily on each call). The discovery
# tools read settings at call time, so updating settings between tests works.
from app.config import settings


_AID_RE = re.compile(r"\bAID-[A-Z]+(?:-\d+(?:\.\d+)?)?\b")


def _make_store(td: Path) -> Path:
    """Create a minimal aidefend-discovery sqlite v1 store with a few rows."""
    db = td / "discovery.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE connector_state (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at TEXT NOT NULL, source TEXT NOT NULL, params TEXT NOT NULL
        );
        CREATE TABLE candidates (
            content_hash TEXT PRIMARY KEY,
            id TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            source_type TEXT, source_id TEXT, feed_url TEXT,
            retrieved_at TEXT NOT NULL, payload TEXT NOT NULL,
            first_seen_run INTEGER, last_seen_run INTEGER,
            promoted_pr_url TEXT, rejected_reason TEXT, review_updated_at TEXT
        );
        CREATE TABLE gap_reports (
            run_id INTEGER NOT NULL, candidate_id TEXT NOT NULL,
            max_bm25 REAL, is_gap INTEGER NOT NULL, gap_reason TEXT, payload TEXT NOT NULL,
            PRIMARY KEY (run_id, candidate_id)
        );
        CREATE TABLE seen_window (
            feed_url TEXT, entry_id TEXT, window_key TEXT, seen_at TEXT,
            PRIMARY KEY (feed_url, entry_id, window_key)
        );
        PRAGMA user_version = 1;
        """
    )
    cand_payload = {
        "id": "candidate-ghsa-deadbeefdeadbeef",
        "title": "GHSA test advisory",
        "summary": "Improper input validation in the foo agent toolchain.",
        "source_urls": ["https://github.com/advisories/GHSA-deadbeef"],
        "entities": {"cves": ["CVE-2026-9999"], "cwes": ["CWE-94"], "ghsas": ["ghsa-deadbeefdeadbeef"]},
        "retrieved_at": "2026-05-03T00:00:00Z",
    }
    gr_payload = {
        "candidate_id": cand_payload["id"],
        "nearest_technique_ids": ["AID-H-001", "AID-H-002"],
        "bm25_scores": [9.5, 7.0],
        "max_bm25": 9.5,
        "threat_id_overlap": [],
        "candidate_threat_tokens": [],
        "is_gap": False,
        "gap_reason": "not_gap",
        "suggested_tactic_ids": ["harden"],
        "suggested_pillars": ["model"],
        "suggested_phases": ["operation"],
        "rationale": "test",
        "nearest_lexical_overlap_terms": [["foo", "agent"], []],
        "bridge_rationales": [
            "CWE-94: Code injection via LLM-generated code (conf 0.85; src https://cwe.mitre.org/data/definitions/94.html)"
        ],
    }
    conn.execute("INSERT INTO runs(generated_at, source, params) VALUES ('2026-05-03T00:00:00Z', 'ghsa', '{}')")
    conn.execute(
        """
        INSERT INTO candidates(content_hash, id, status, source_type, source_id, feed_url, retrieved_at, payload, first_seen_run, last_seen_run)
        VALUES ('hash1', ?, 'candidate', 'ghsa_api', 'GHSA-deadbeef', 'ghsa_api', '2026-05-03T00:00:00Z', ?, 1, 1)
        """,
        (cand_payload["id"], json.dumps(cand_payload)),
    )
    conn.execute(
        """
        INSERT INTO gap_reports(run_id, candidate_id, max_bm25, is_gap, gap_reason, payload)
        VALUES (1, ?, 9.5, 0, 'not_gap', ?)
        """,
        (cand_payload["id"], json.dumps(gr_payload)),
    )
    conn.commit()
    conn.close()
    return db


def _make_anchor_diff_report(td: Path) -> Path:
    reports = td / "reports"
    reports.mkdir(exist_ok=True)
    p = reports / "anchor_diff_20260503.json"
    p.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-03T00:00:00Z",
                "data_json": "/fake/data.json",
                "framework_count": 2,
                "diffs": [
                    {
                        "framework": "OWASP LLM Top 10 2025",
                        "version": "2025",
                        "snapshot_date": "2026-05-03",
                        "source_url": "https://owasp.org/...",
                        "anchor_item_count": 10,
                        "missing_from_aidefend": [],
                        "present_in_aidefend": [{"id": "LLM01:2025", "matched": "LLM01:2025 Prompt Injection"}],
                        "unmatched_aidefend_items": [],
                        "coverage_ratio": 1.0,
                    },
                    {
                        "framework": "OWASP Agentic AI Top 10 2026",
                        "version": "2026",
                        "snapshot_date": "2026-05-03",
                        "source_url": "https://owasp.org/...",
                        "anchor_item_count": 10,
                        "missing_from_aidefend": [{"id": "ASI11:2026", "title": "Future entry"}],
                        "present_in_aidefend": [],
                        "unmatched_aidefend_items": [],
                        "coverage_ratio": 0.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture
def configured_store(monkeypatch):
    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        db = _make_store(td)
        _make_anchor_diff_report(td)
        monkeypatch.setattr(settings, "DISCOVERY_DB_PATH", db)
        monkeypatch.setattr(settings, "DISCOVERY_REPORTS_PATH", td / "reports")
        yield db


@pytest.fixture
def unconfigured_store(monkeypatch):
    monkeypatch.setattr(settings, "DISCOVERY_DB_PATH", None)
    monkeypatch.setattr(settings, "DISCOVERY_REPORTS_PATH", None)
    yield None


# === search_discovery_candidates ===

@pytest.mark.asyncio
async def test_search_returns_namespace_marker_when_configured(configured_store):
    from app.tools.search_discovery_candidates import search_discovery_candidates
    res = await search_discovery_candidates(top_k=10)
    assert res["discovery_namespace"] is True
    assert res["configured"] is True
    assert "disclaimer" in res
    assert "Hypothesis only" in res["disclaimer"]


@pytest.mark.asyncio
async def test_search_returns_namespace_marker_when_unconfigured(unconfigured_store):
    from app.tools.search_discovery_candidates import search_discovery_candidates
    res = await search_discovery_candidates(top_k=10)
    assert res["discovery_namespace"] is True
    assert res["configured"] is False
    assert "DISCOVERY_DB_PATH" in res["error"]


@pytest.mark.asyncio
async def test_search_no_aid_ids_in_primary_fields(configured_store):
    """Contract: AID-* IDs only allowed inside `references_aid` sidecar."""
    from app.tools.search_discovery_candidates import search_discovery_candidates
    res = await search_discovery_candidates(top_k=10)
    primary = res["results"][0]
    # Pull a stringified version excluding the references_aid sidecar
    sanitized = dict(primary)
    sanitized.pop("references_aid", None)
    sanitized.pop("references_aid_note", None)
    sanitized.pop("suggested_tactic_hints", None)
    text = json.dumps(sanitized)
    assert _AID_RE.search(text) is None, f"AID-* found in primary fields: {text!r}"


@pytest.mark.asyncio
async def test_search_references_aid_carries_disclaimer(configured_store):
    from app.tools.search_discovery_candidates import search_discovery_candidates
    res = await search_discovery_candidates(top_k=10)
    primary = res["results"][0]
    assert "AID-H-001" in primary["references_aid"]
    assert "Hypothesis only" in primary["references_aid_note"]


# === explain_candidate_mapping ===

@pytest.mark.asyncio
async def test_explain_cites_at_least_one_source_url(configured_store):
    from app.tools.explain_candidate_mapping import explain_candidate_mapping
    res = await explain_candidate_mapping("candidate-ghsa-deadbeefdeadbeef")
    assert res["discovery_namespace"] is True
    assert "candidate" in res
    assert len(res["candidate"]["source_urls"]) >= 1


@pytest.mark.asyncio
async def test_explain_returns_bridge_rationales(configured_store):
    from app.tools.explain_candidate_mapping import explain_candidate_mapping
    res = await explain_candidate_mapping("candidate-ghsa-deadbeefdeadbeef")
    assert res["candidate"].get("bridge_rationales")
    assert "CWE-94" in res["candidate"]["bridge_rationales"][0]


@pytest.mark.asyncio
async def test_explain_unknown_candidate_returns_namespaced_error(configured_store):
    from app.tools.explain_candidate_mapping import explain_candidate_mapping
    res = await explain_candidate_mapping("candidate-does-not-exist")
    assert res["discovery_namespace"] is True
    assert res["configured"] is True
    assert "not found" in res["error"]


@pytest.mark.asyncio
async def test_explain_empty_id_returns_error(configured_store):
    from app.tools.explain_candidate_mapping import explain_candidate_mapping
    res = await explain_candidate_mapping("")
    assert res["discovery_namespace"] is True
    assert "candidate_id" in res["error"]


@pytest.mark.asyncio
async def test_explain_unconfigured_returns_namespace_marker(unconfigured_store):
    from app.tools.explain_candidate_mapping import explain_candidate_mapping
    res = await explain_candidate_mapping("anything")
    assert res["discovery_namespace"] is True
    assert res["configured"] is False


# === list_anchor_diff ===

@pytest.mark.asyncio
async def test_anchor_diff_returns_namespace_marker(configured_store):
    from app.tools.list_anchor_diff import list_anchor_diff
    res = await list_anchor_diff()
    assert res["discovery_namespace"] is True
    assert res["configured"] is True
    assert res["framework_count"] == 2


@pytest.mark.asyncio
async def test_anchor_diff_filter(configured_store):
    from app.tools.list_anchor_diff import list_anchor_diff
    res = await list_anchor_diff(framework="Agentic")
    assert res["framework_count"] == 1
    assert "ASI11:2026" in {m["id"] for m in res["diffs"][0]["missing_from_aidefend"]}


@pytest.mark.asyncio
async def test_anchor_diff_unconfigured_returns_namespace_marker(unconfigured_store):
    from app.tools.list_anchor_diff import list_anchor_diff
    res = await list_anchor_diff()
    assert res["discovery_namespace"] is True
    assert res["configured"] is False


@pytest.mark.asyncio
async def test_anchor_diff_ids_note_warns_about_namespace(configured_store):
    from app.tools.list_anchor_diff import list_anchor_diff
    res = await list_anchor_diff()
    assert "not AIDEFEND AID-* IDs" in res["ids_note"]


# === Cross-tool wall test ===

@pytest.mark.asyncio
async def test_no_tool_returns_aid_ids_in_top_level_keys(configured_store):
    """The top-level dict keys (and immediate string values) of every discovery
    response must not be AID-* IDs. Only `references_aid` (a list) and
    `suggested_tactic_hints` may carry them."""
    from app.tools.search_discovery_candidates import search_discovery_candidates
    from app.tools.list_anchor_diff import list_anchor_diff

    s = await search_discovery_candidates(top_k=5)
    a = await list_anchor_diff()
    for resp in (s, a):
        # Top-level scalar / list checks: no AID-* in JSON-stringified
        # version *excluding* references_aid (sidecar) and gap_report block.
        copy = dict(resp)
        for r in copy.get("results", []) or []:
            r.pop("references_aid", None)
            r.pop("references_aid_note", None)
            r.pop("suggested_tactic_hints", None)
        # Strip nested gap_report (which legitimately holds AID-* in
        # nearest_technique_ids — that's not a primary field, but the
        # explain_candidate_mapping test above asserts that explicitly).
        text = json.dumps(copy)
        assert _AID_RE.search(text) is None, f"AID-* leaked in primary fields: {text[:300]}"
