"""Local API and sqlite review store for the AIDEFEND Discovery review console."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
import sys
import threading
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

try:
    import export_review_digest
except ModuleNotFoundError:  # pragma: no cover - direct module execution fallback
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import export_review_digest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from aidefend_discovery.baseline import flatten_techniques, load_data_json  # noqa: E402
from aidefend_discovery.bridge import default_bridge_path, load_bridge  # noqa: E402
from aidefend_discovery.bm25_index import BM25Index  # noqa: E402
from aidefend_discovery.extract import enrich_candidate, load_host_allowlist  # noqa: E402
from aidefend_discovery.ghsa_ingest import ingest_ghsa_incremental  # noqa: E402
from aidefend_discovery.nvd_ingest import ingest_nvd_incremental  # noqa: E402
from aidefend_discovery.rss_ingest import (  # noqa: E402
    append_jsonl,
    entry_to_candidate,
    fetch_feed_xml,
    ingest_allowlisted_feed,
    load_allowlist,
    parse_feed_entries,
)
from aidefend_discovery.state_store import (  # noqa: E402
    record_gap_report,
    record_run,
    upsert_candidate,
)
from run_discovery_gap import build_gap_report  # noqa: E402

DEFAULT_SAMPLE_REPORT = ROOT / "tests" / "fixtures" / "sample_gap_run.json"
DEFAULT_REPORT = DEFAULT_SAMPLE_REPORT
DEFAULT_DB = ROOT / "lab" / "aidefend_discovery" / "review_console.db"
DEFAULT_STATIC_DIR = ROOT / "review_console" / "dist"
DEFAULT_DATA_JSON = ROOT / "vendor" / "aidefense-framework" / "data" / "data.json"
DEFAULT_REPORTS_DIR = ROOT / "reports" / "demo"
DEFAULT_ALLOWLIST = ROOT / "lab" / "aidefend_discovery" / "feeds.allowlist"
DEFAULT_PAGE_ALLOWLIST = ROOT / "lab" / "aidefend_discovery" / "page_fetch.allowlist"
DEFAULT_DISCOVERY_DB = ROOT / "lab" / "aidefend_discovery" / "discovery_state.db"
DEFAULT_CANDIDATES_OUT = ROOT / "lab" / "aidefend_discovery" / "candidates.jsonl"

REVIEW_DECISIONS = {
    "promote": "Promote",
    "merge": "Merge Into Existing",
    "reject": "Reject",
    "needs_evidence": "Needs Evidence",
    "monitor": "Monitor",
}

PRESETS = [
    {
        "id": "quick_demo",
        "label": "Quick Demo: sample report",
        "short_label": "Run sample demo",
        "description": "Loads the checked-in sample report. No network or API keys.",
        "sources": ["sample"],
        "network": False,
    },
    {
        "id": "rss_ai_releases",
        "label": "RSS: AI framework releases",
        "short_label": "Start quick scan",
        "description": "Fetches one allowlisted AI framework release feed and maps candidates.",
        "sources": ["rss"],
        "network": True,
    },
    {
        "id": "nvd_ai_ml",
        "label": "NVD: AI/ML keyword scan",
        "short_label": "Scan NVD",
        "description": "Queries NVD for recent AI/ML keyword matches. NVD_API_KEY improves rate limits.",
        "sources": ["nvd"],
        "network": True,
    },
    {
        "id": "ghsa_high",
        "label": "GHSA: high-severity advisories",
        "short_label": "Scan GHSA",
        "description": "Queries GitHub Security Advisories for recent high-severity advisories.",
        "sources": ["ghsa"],
        "network": True,
    },
    {
        "id": "full_sweep",
        "label": "Full Sweep: RSS + NVD + GHSA",
        "short_label": "Full sweep",
        "description": "Runs RSS, NVD, and GHSA into one merged candidate queue.",
        "sources": ["rss", "nvd", "ghsa"],
        "network": True,
    },
]

TACTIC_FILES = {
    "AID-M": "vendor/aidefense-framework/tactics/model.js",
    "model": "vendor/aidefense-framework/tactics/model.js",
    "AID-H": "vendor/aidefense-framework/tactics/harden.js",
    "harden": "vendor/aidefense-framework/tactics/harden.js",
    "AID-D": "vendor/aidefense-framework/tactics/detect.js",
    "detect": "vendor/aidefense-framework/tactics/detect.js",
    "AID-I": "vendor/aidefense-framework/tactics/isolate.js",
    "isolate": "vendor/aidefense-framework/tactics/isolate.js",
    "AID-DV": "vendor/aidefense-framework/tactics/deceive.js",
    "deceive": "vendor/aidefense-framework/tactics/deceive.js",
    "AID-E": "vendor/aidefense-framework/tactics/evict.js",
    "evict": "vendor/aidefense-framework/tactics/evict.js",
    "AID-R": "vendor/aidefense-framework/tactics/restore.js",
    "restore": "vendor/aidefense-framework/tactics/restore.js",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _join_text(values: list[Any], fallback: str = "None observed") -> str:
    parts = [str(value) for value in values if str(value)]
    return ", ".join(parts) if parts else fallback


def _entities(candidate: dict[str, Any]) -> dict[str, list[Any]]:
    value = candidate.get("entities") or {}
    if not isinstance(value, dict):
        return {}
    return {str(k): _as_list(v) for k, v in value.items()}


def candidate_key(candidate: dict[str, Any], report_id: str | None = None) -> str:
    """Stable candidate-local identity with documented fallbacks."""
    if candidate.get("content_hash"):
        return f"content:{candidate['content_hash']}"
    source_type = _text(candidate.get("source_type") or candidate.get("feed_url")).strip()
    source_id = _text(candidate.get("source_id")).strip()
    if source_type and source_id:
        return f"source:{source_type}:{source_id}"
    cand_id = _text(candidate.get("id")).strip()
    if cand_id:
        return f"candidate:{cand_id}"
    basis = _json(candidate)
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"generated:{report_id or 'report'}:{digest}"


def source_label(candidate: dict[str, Any]) -> str:
    raw = _text(candidate.get("source_type") or candidate.get("feed_url")).lower()
    source_id = _text(candidate.get("source_id")).lower()
    if "ghsa" in raw or source_id.startswith("ghsa-"):
        return "GHSA"
    if "nvd" in raw or source_id.startswith("cve-"):
        return "NVD"
    if "rss" in raw:
        return "RSS"
    return raw.upper() if raw else "UNKNOWN"


def severity(candidate: dict[str, Any]) -> str:
    for key in ("severity", "ghsa_severity", "nvd_severity", "cvss_severity"):
        value = _text(candidate.get(key)).strip().lower()
        if value:
            return value
    return "unknown"


def ecosystem(candidate: dict[str, Any]) -> str:
    for item in _as_list(candidate.get("ghsa_packages") or candidate.get("packages")):
        text = _text(item)
        if ":" in text:
            return text.split(":", 1)[0]
    return ""


def reason_chips(row: export_review_digest.DigestRow) -> list[str]:
    chips: list[str] = []
    candidate = row.candidate
    gap = row.gap_report
    if row.coverage_score <= 40:
        chips.append("low coverage")
    if source_label(candidate) == "GHSA":
        chips.append("reviewed GHSA")
    if _entities(candidate).get("cwes") or _as_list(gap.get("bridge_rationales")):
        chips.append("CWE bridge")
    if row.security_score >= 80:
        chips.append("high severity")
    if row.recommended_action == export_review_digest.ACTION_NEEDS_EVIDENCE:
        chips.append("weak evidence")
    return chips


@dataclass(frozen=True)
class ReportSession:
    report_path: Path
    payload: dict[str, Any]
    rows: list[export_review_digest.DigestRow]
    report_id: str

    @classmethod
    def load(cls, report_path: Path) -> "ReportSession":
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        rows = export_review_digest.build_rows(payload)
        digest = hashlib.sha256(report_path.read_bytes()).hexdigest()[:16]
        return cls(report_path=report_path, payload=payload, rows=rows, report_id=digest)

    def find_row(self, key_or_id: str) -> export_review_digest.DigestRow | None:
        for row in self.rows:
            if row.candidate_id == key_or_id or candidate_key(row.candidate, self.report_id) == key_or_id:
                return row
        return None


class ReviewStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_decisions (
                    candidate_key TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    content_hash TEXT,
                    source_type TEXT,
                    source_id TEXT,
                    report_id TEXT,
                    review_decision TEXT NOT NULL,
                    reviewer_notes TEXT,
                    assigned_owner TEXT,
                    confidence TEXT,
                    merge_target TEXT,
                    promotion_target TEXT,
                    proposed_tactic TEXT,
                    proposed_title TEXT,
                    supporting_evidence TEXT,
                    nearest_checked TEXT,
                    evidence_to_add TEXT,
                    not_new_reason TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(self, row: export_review_digest.DigestRow, report_id: str, data: dict[str, Any]) -> dict[str, Any]:
        decision = _text(data.get("review_decision")).strip()
        if decision not in REVIEW_DECISIONS:
            raise ValueError("review_decision must be one of: " + ", ".join(sorted(REVIEW_DECISIONS)))
        candidate = row.candidate
        key = candidate_key(candidate, report_id)
        values = {
            "candidate_key": key,
            "candidate_id": row.candidate_id,
            "content_hash": candidate.get("content_hash"),
            "source_type": candidate.get("source_type") or candidate.get("feed_url"),
            "source_id": candidate.get("source_id"),
            "report_id": report_id,
            "review_decision": decision,
            "reviewer_notes": data.get("reviewer_notes", ""),
            "assigned_owner": data.get("assigned_owner", ""),
            "confidence": data.get("confidence", ""),
            "merge_target": data.get("merge_target", ""),
            "promotion_target": data.get("promotion_target", ""),
            "proposed_tactic": data.get("proposed_tactic", ""),
            "proposed_title": data.get("proposed_title", ""),
            "supporting_evidence": data.get("supporting_evidence", ""),
            "nearest_checked": data.get("nearest_checked", ""),
            "evidence_to_add": data.get("evidence_to_add", ""),
            "not_new_reason": data.get("not_new_reason", ""),
            "updated_at": _now_iso(),
        }
        columns = list(values)
        update = ", ".join(f"{col}=excluded.{col}" for col in columns if col != "candidate_key")
        with self.connect() as conn:
            conn.execute(
                f"""
                INSERT INTO review_decisions({", ".join(columns)})
                VALUES({", ".join("?" for _ in columns)})
                ON CONFLICT(candidate_key) DO UPDATE SET {update}
                """,
                [values[col] for col in columns],
            )
        return self.get(key) or {}

    def get(self, key: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM review_decisions WHERE candidate_key = ?", (key,)).fetchone()
        return dict(row) if row else None

    def reviewed_keys(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT candidate_key FROM review_decisions").fetchall()
        return {str(row["candidate_key"]) for row in rows}


def reviewed_count_for_session(session: ReportSession, store: ReviewStore) -> int:
    reviewed = store.reviewed_keys()
    return sum(
        1
        for row in session.rows
        if candidate_key(row.candidate, session.report_id) in reviewed
    )


def row_summary(row: export_review_digest.DigestRow, report_id: str, review: dict[str, Any] | None) -> dict[str, Any]:
    candidate = row.candidate
    entities = _entities(candidate)
    return {
        "candidate_key": candidate_key(candidate, report_id),
        "candidate_id": row.candidate_id,
        "title": row.title,
        "source_type": source_label(candidate),
        "source_id": candidate.get("source_id") or row.candidate_id,
        "severity": severity(candidate),
        "ecosystem": ecosystem(candidate),
        "coverage_score": row.coverage_score,
        "security_score": row.security_score,
        "recommended_action": row.recommended_action,
        "review_status": review.get("review_decision") if review else "unreviewed",
        "review_decision_label": REVIEW_DECISIONS.get(review.get("review_decision", ""), "") if review else "",
        "identifiers": {
            "cves": entities.get("cves", []),
            "ghsas": entities.get("ghsas", []),
            "cwes": entities.get("cwes", []),
        },
        "reason_chips": reason_chips(row),
    }


def row_detail(row: export_review_digest.DigestRow, report_id: str, review: dict[str, Any] | None) -> dict[str, Any]:
    summary = row_summary(row, report_id, review)
    candidate = row.candidate
    gap = row.gap_report
    entities = _entities(candidate)
    nearest = []
    ids = _as_list(gap.get("nearest_technique_ids"))
    overlaps = _as_list(gap.get("nearest_lexical_overlap_terms"))
    scores = _as_list(gap.get("bm25_scores"))
    for idx, technique_id in enumerate(ids):
        nearest.append(
            {
                "id": technique_id,
                "name": technique_id,
                "bm25_score": scores[idx] if idx < len(scores) else None,
                "lexical_overlap": overlaps[idx] if idx < len(overlaps) else [],
                "coverage_note": "Potential existing coverage" if row.coverage_score >= 60 else "Review coverage gap",
            }
        )
    source_urls = _as_list(candidate.get("source_urls"))
    return {
        **summary,
        "review": review,
        "sections": {
            "what_this_is": export_review_digest._truncate(
                candidate.get("summary") or candidate.get("summary_raw") or "No summary available.", 900
            ),
            "why_care": export_review_digest._why_care(row),
            "coverage_assessment": export_review_digest._coverage_assessment(row),
            "security_assessment": export_review_digest._security_assessment(row),
            "evidence": {
                "identifiers": summary["identifiers"],
                "packages": _as_list(candidate.get("ghsa_packages") or candidate.get("packages")),
                "versions": entities.get("version_constraints", []),
                "source_urls": source_urls,
                "bridge_rationales": _as_list(gap.get("bridge_rationales")),
            },
            "similar_techniques": nearest,
            "provenance": {
                "candidate_id": row.candidate_id,
                "candidate_key": summary["candidate_key"],
                "source_type": candidate.get("source_type") or candidate.get("feed_url") or "unknown",
                "source_id": candidate.get("source_id") or "unknown",
                "source_url": source_urls[0] if source_urls else "",
                "retrieved_at": candidate.get("retrieved_at") or "unknown",
                "max_bm25": gap.get("max_bm25"),
                "gap_bm25_max": row.gap_bm25_max,
                "coverage_ceiling": row.coverage_ceiling,
                "source_severity": severity(candidate),
                "raw_score_details": export_review_digest._raw_score_details(row),
                "gap_reason": gap.get("gap_reason") or "missing",
                "bridge_rationale": "; ".join(_as_list(gap.get("bridge_rationales"))),
                "license_note": candidate.get("license_note") or "unknown",
                "raw_candidate": candidate,
                "raw_gap_report": gap,
            },
        },
    }


def filtered_rows(session: ReportSession, store: ReviewStore, params: dict[str, list[str]]) -> list[dict[str, Any]]:
    tab = params.get("tab", ["lowest"])[0]
    reviewed = store.reviewed_keys()
    summaries = []
    for row in session.rows:
        key = candidate_key(row.candidate, session.report_id)
        review = store.get(key)
        item = row_summary(row, session.report_id, review)
        if tab == "lowest" and "low coverage" not in item["reason_chips"]:
            continue
        if tab == "highest" and row.security_score < 80:
            continue
        if tab == "needs_evidence" and row.recommended_action != export_review_digest.ACTION_NEEDS_EVIDENCE:
            continue
        if tab == "monitor" and row.recommended_action != export_review_digest.ACTION_MONITOR:
            continue
        if tab == "reviewed" and key not in reviewed:
            continue
        if params.get("source_type", [""])[0] and item["source_type"] != params["source_type"][0]:
            continue
        if params.get("severity", [""])[0] and item["severity"] != params["severity"][0]:
            continue
        if params.get("reviewed", [""])[0] == "reviewed" and key not in reviewed:
            continue
        if params.get("reviewed", [""])[0] == "unreviewed" and key in reviewed:
            continue
        cwe = params.get("cwe", [""])[0].strip().upper()
        if cwe and cwe not in {str(v).upper() for v in item["identifiers"]["cwes"]}:
            continue
        ecosystem_value = params.get("ecosystem", [""])[0].strip()
        if ecosystem_value and item["ecosystem"] != ecosystem_value:
            continue
        min_cov = params.get("coverage_min", [""])[0]
        max_cov = params.get("coverage_max", [""])[0]
        try:
            if min_cov and row.coverage_score < int(min_cov):
                continue
            if max_cov and row.coverage_score > int(max_cov):
                continue
        except ValueError:
            pass
        summaries.append(item)
    if tab == "highest":
        summaries.sort(key=lambda x: (-x["security_score"], x["coverage_score"], x["title"]))
    else:
        summaries.sort(key=lambda x: (x["coverage_score"], -x["security_score"], x["title"]))
    return summaries


def export_reviewed_markdown(session: ReportSession, store: ReviewStore) -> str:
    lines = [
        "# AIDEFEND Discovery Reviewed Candidate Export",
        "",
        f"- Input report: {session.report_path}",
        f"- Exported at: {_now_iso()}",
        "",
    ]
    count = 0
    for row in session.rows:
        key = candidate_key(row.candidate, session.report_id)
        review = store.get(key)
        if not review:
            continue
        detail = row_detail(row, session.report_id, review)
        prov = detail["sections"]["provenance"]
        count += 1
        lines.extend(
            [
                f"## {detail['title']}",
                "",
                f"- Candidate ID: {detail['candidate_id']}",
                f"- Backend recommended action: {detail['recommended_action']}",
                f"- Reviewer decision: {REVIEW_DECISIONS.get(review['review_decision'], review['review_decision'])}",
                f"- Owner: {review.get('assigned_owner') or 'Unassigned'}",
                f"- Confidence: {review.get('confidence') or 'Unspecified'}",
                f"- Coverage Score: {detail['coverage_score']}/100",
                f"- Security Score: {detail['security_score']}/100",
                f"- Source: {prov['source_type']} {prov['source_id']}",
                f"- Source URL: {prov['source_url'] or 'None observed'}",
                f"- Retrieved at: {prov['retrieved_at']}",
                f"- Raw score details: {prov['raw_score_details']}",
                "",
                "### Reviewer Notes",
                "",
                review.get("reviewer_notes") or "No notes recorded.",
                "",
                "### Decision Fields",
                "",
                f"- Merge target: {review.get('merge_target') or 'None'}",
                f"- Promotion target: {review.get('promotion_target') or 'None'}",
                f"- Proposed tactic: {review.get('proposed_tactic') or 'None'}",
                f"- Proposed title: {review.get('proposed_title') or 'None'}",
                f"- Supporting evidence: {review.get('supporting_evidence') or 'None'}",
                f"- Nearest existing techniques checked: {review.get('nearest_checked') or 'None'}",
                f"- Evidence to add: {review.get('evidence_to_add') or 'None'}",
                f"- Why not new: {review.get('not_new_reason') or 'None'}",
                "",
            ]
        )
    if count == 0:
        lines.append("No reviewed candidates.")
    return "\n".join(lines)


def export_reviewed_csv(session: ReportSession, store: ReviewStore) -> str:
    fields = [
        "candidate_id",
        "candidate_key",
        "title",
        "source_type",
        "source_id",
        "coverage_score",
        "security_score",
        "backend_recommended_action",
        "review_decision",
        "reviewer_notes",
        "assigned_owner",
        "confidence",
        "merge_target",
        "promotion_target",
        "proposed_tactic",
        "proposed_title",
        "supporting_evidence",
        "nearest_checked",
        "evidence_to_add",
        "not_new_reason",
        "source_url",
        "retrieved_at",
        "max_bm25",
        "gap_bm25_max",
        "gap_reason",
        "bridge_rationale",
    ]
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in session.rows:
        key = candidate_key(row.candidate, session.report_id)
        review = store.get(key)
        if not review:
            continue
        detail = row_detail(row, session.report_id, review)
        prov = detail["sections"]["provenance"]
        writer.writerow(
            {
                "candidate_id": detail["candidate_id"],
                "candidate_key": key,
                "title": detail["title"],
                "source_type": prov["source_type"],
                "source_id": prov["source_id"],
                "coverage_score": detail["coverage_score"],
                "security_score": detail["security_score"],
                "backend_recommended_action": detail["recommended_action"],
                "review_decision": review["review_decision"],
                "reviewer_notes": review.get("reviewer_notes") or "",
                "assigned_owner": review.get("assigned_owner") or "",
                "confidence": review.get("confidence") or "",
                "merge_target": review.get("merge_target") or "",
                "promotion_target": review.get("promotion_target") or "",
                "proposed_tactic": review.get("proposed_tactic") or "",
                "proposed_title": review.get("proposed_title") or "",
                "supporting_evidence": review.get("supporting_evidence") or "",
                "nearest_checked": review.get("nearest_checked") or "",
                "evidence_to_add": review.get("evidence_to_add") or "",
                "not_new_reason": review.get("not_new_reason") or "",
                "source_url": prov["source_url"],
                "retrieved_at": prov["retrieved_at"],
                "max_bm25": prov["max_bm25"],
                "gap_bm25_max": prov["gap_bm25_max"],
                "gap_reason": prov["gap_reason"],
                "bridge_rationale": prov["bridge_rationale"],
            }
        )
    return out.getvalue()


def export_candidates_csv(session: ReportSession, store: ReviewStore) -> str:
    fields = [
        "candidate_id",
        "candidate_key",
        "title",
        "source_type",
        "source_id",
        "severity",
        "coverage_score",
        "security_score",
        "backend_recommended_action",
        "review_decision",
        "reviewer_notes",
        "assigned_owner",
        "confidence",
        "source_urls",
        "content_hash",
        "nearest_technique_ids",
        "max_bm25",
        "gap_reason",
        "bridge_rationales",
    ]
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in session.rows:
        key = candidate_key(row.candidate, session.report_id)
        review = store.get(key) or {}
        detail = row_detail(row, session.report_id, review if review else None)
        prov = detail["sections"]["provenance"]
        evidence = detail["sections"]["evidence"]
        writer.writerow(
            {
                "candidate_id": detail["candidate_id"],
                "candidate_key": key,
                "title": detail["title"],
                "source_type": prov["source_type"],
                "source_id": prov["source_id"],
                "severity": detail["severity"],
                "coverage_score": detail["coverage_score"],
                "security_score": detail["security_score"],
                "backend_recommended_action": detail["recommended_action"],
                "review_decision": review.get("review_decision", ""),
                "reviewer_notes": review.get("reviewer_notes", ""),
                "assigned_owner": review.get("assigned_owner", ""),
                "confidence": review.get("confidence", ""),
                "source_urls": "; ".join(evidence["source_urls"]),
                "content_hash": row.candidate.get("content_hash", ""),
                "nearest_technique_ids": "; ".join(_as_list(row.gap_report.get("nearest_technique_ids"))),
                "max_bm25": prov["max_bm25"],
                "gap_reason": prov["gap_reason"],
                "bridge_rationales": "; ".join(evidence["bridge_rationales"]),
            }
        )
    return out.getvalue()


def export_session_json(session: ReportSession, store: ReviewStore) -> str:
    reviews: dict[str, Any] = {}
    for row in session.rows:
        key = candidate_key(row.candidate, session.report_id)
        review = store.get(key)
        if review:
            reviews[key] = review
    payload = {
        "disclaimer": (
            "AIDEFEND Discovery output is candidate-only. Reviewer decisions and backend "
            "recommendations are not approved AIDEFEND truth."
        ),
        "report_id": session.report_id,
        "report_path": str(session.report_path),
        "exported_at": _now_iso(),
        "payload": session.payload,
        "review_decisions": reviews,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _promotion_shape(detail: dict[str, Any], review: dict[str, Any] | None) -> str:
    decision = (review or {}).get("review_decision") or ""
    gap = detail["sections"]["provenance"].get("gap_reason") or ""
    if decision == "merge" or detail["coverage_score"] >= 60:
        return "Shape A: extend an existing technique's defendsAgainst mapping"
    if decision == "promote" or (detail["coverage_score"] <= 40 and "not_gap" not in gap):
        return "Shape B: draft a new technique candidate"
    if decision == "reject":
        return "No promotion: reject candidate"
    if decision == "needs_evidence":
        return "Hold: needs evidence before promotion shape is chosen"
    return "Monitor: no promotion shape yet"


def _suggested_tactic_file(gap_report: dict[str, Any], review: dict[str, Any] | None) -> str:
    target = (review or {}).get("promotion_target") or ""
    if target:
        return str(target)
    for hint in _as_list(gap_report.get("suggested_tactic_ids")):
        if str(hint) in TACTIC_FILES:
            return TACTIC_FILES[str(hint)]
    for technique_id in _as_list(gap_report.get("nearest_technique_ids")):
        prefix = "-".join(str(technique_id).split("-")[:2])
        if prefix in TACTIC_FILES:
            return TACTIC_FILES[prefix]
    return "vendor/aidefense-framework/tactics/<reviewer-selected>.js"


def export_action_packet(session: ReportSession, store: ReviewStore, key_or_id: str) -> str:
    row = session.find_row(key_or_id)
    if not row:
        raise KeyError("Candidate not found.")
    key = candidate_key(row.candidate, session.report_id)
    review = store.get(key)
    detail = row_detail(row, session.report_id, review)
    prov = detail["sections"]["provenance"]
    evidence = detail["sections"]["evidence"]
    nearest = detail["sections"]["similar_techniques"]
    shape = _promotion_shape(detail, review)
    tactic_file = _suggested_tactic_file(row.gap_report, review)
    source_lines = [f"  - {url}" for url in evidence["source_urls"]] or ["  - None observed"]
    nearest_ids = ", ".join(t["id"] for t in nearest) or "None observed"
    lexical = "; ".join(
        f"{t['id']}: {', '.join(t['lexical_overlap']) or 'no lexical overlap'}"
        for t in nearest[:3]
    ) or "None observed"
    reviewer_notes = (review or {}).get("reviewer_notes") or "No reviewer notes recorded."
    confidence = (review or {}).get("confidence") or str(row.candidate.get("confidence") or "unspecified")
    try:
        producer_confidence = float(row.candidate.get("confidence") or 0)
    except (TypeError, ValueError):
        producer_confidence = 0.0
    high_confidence = str(confidence).lower() == "high" or producer_confidence >= 0.85

    lines = [
        f"# Action Packet: {detail['title']}",
        "",
        "> Candidate-only maintainer packet. This is not approved AIDEFEND truth.",
        "",
        "## PR-style description",
        "",
        f"## Discovery promotion: {detail['title']}",
        "",
        f"- **Discovery candidate:** `{detail['candidate_id']}` (`source_type={prov['source_type']}`, `source_id={prov['source_id']}`)",
        "- **Source URLs:**",
        *source_lines,
        f"- **content_hash:** `{row.candidate.get('content_hash') or 'missing'}`",
        "- **GapReport summary:**",
        f"  - `nearest_technique_ids`: {nearest_ids}",
        f"  - `max_bm25`: {prov['max_bm25']}",
        f"  - `gap_reason`: `{prov['gap_reason']}`",
        f"  - `nearest_lexical_overlap_terms`: {lexical}",
        f"- **Promotion shape:** {shape}",
        "- **Anchor-diff status:** run `python3 scripts/anchor_diff.py --output reports/anchor_diff_$(date -u +%Y%m%d).json` before PR",
        f"- **kev_flag:** {str(bool(row.candidate.get('kev_flag'))).lower()}",
        f"- **Reviewer decision:** {REVIEW_DECISIONS.get((review or {}).get('review_decision', ''), 'Unreviewed')}",
        f"- **Reviewer confidence:** {confidence}",
        f"- **Reviewer notes:** {reviewer_notes}",
        "",
        "Closes loop for discovery candidate: `" + detail["candidate_id"] + "`",
        "",
        "## Maintainer review notes",
        "",
        f"- Recommended file: `{tactic_file}`",
        f"- Suggested tactic hints: {', '.join(_as_list(row.gap_report.get('suggested_tactic_ids'))) or 'None observed'}",
        f"- Bridge rationales: {'; '.join(evidence['bridge_rationales']) or 'None observed'}",
        f"- Source identifiers: CVE={_join_text(evidence['identifiers']['cves'])}; GHSA={_join_text(evidence['identifiers']['ghsas'])}; CWE={_join_text(evidence['identifiers']['cwes'])}",
        "",
    ]
    if high_confidence and ("Shape A" in shape or "Shape B" in shape):
        lines.extend(
            [
                "## Draft code-change suggestion",
                "",
                "**Human review required.** This is a starting point for `vendor/aidefense-framework/tactics/*.js`, not an automatic edit.",
                "",
                "```js",
                f"// File: {tactic_file}",
            ]
        )
        if "Shape A" in shape:
            target = (review or {}).get("merge_target") or (nearest[0]["id"] if nearest else "<existing AID-* technique>")
            lines.extend(
                [
                    f"// Add source-backed framework item evidence under {target}.",
                    "// Do not paste the candidate title here. Use the exact upstream framework item",
                    "// from anchor-diff/manual review, matching PROMOTION_PLAYBOOK.md.",
                    "defendsAgainst: [",
                    "  {",
                    '    framework: "<reviewer-selected framework>",',
                    '    items: ["<verbatim upstream framework item>"]',
                    "  }",
                    "]",
                ]
            )
        else:
            proposed_title = (review or {}).get("proposed_title") or detail["title"]
            lines.extend(
                [
                    "techniques: [",
                    "  {",
                    '    id: "<next AID-* id>",',
                    f'    name: "{proposed_title}",',
                    '    pillar: ["<reviewer-confirmed pillar>"],',
                    '    phase: ["<reviewer-confirmed phase>"],',
                    '    description: "<paraphrased maintainer-authored description>",',
                    "    defendsAgainst: []",
                    "  }",
                    "]",
                ]
            )
        lines.extend(["```", ""])
    return "\n".join(lines)


def source_health() -> dict[str, Any]:
    try:
        feeds = load_allowlist(DEFAULT_ALLOWLIST)
    except OSError:
        feeds = []
    nvd_key = bool(os.environ.get("NVD_API_KEY", "").strip())
    ghsa_key = bool((os.environ.get("GH_PAT_FOR_GHSA") or os.environ.get("GITHUB_TOKEN") or "").strip())
    ai_key = bool(os.environ.get("AI_SUMMARY_API_KEY", "").strip())
    ai_model = os.environ.get("AI_SUMMARY_MODEL", "").strip()
    ai_base = os.environ.get("AI_SUMMARY_BASE_URL", "").strip()
    return {
        "rss": {
            "label": "RSS",
            "status": "available" if feeds else "unavailable",
            "detail": f"{len(feeds)} allowlisted feed(s)" if feeds else "No allowlisted feeds configured",
            "requires_key": False,
        },
        "nvd": {
            "label": "NVD",
            "status": "key_configured" if nvd_key else "anonymous",
            "detail": "NVD_API_KEY configured" if nvd_key else "Anonymous mode, lower rate limit",
            "requires_key": False,
            "improves_with_key": True,
        },
        "ghsa": {
            "label": "GHSA",
            "status": "key_configured" if ghsa_key else "anonymous",
            "detail": "GitHub token configured" if ghsa_key else "Anonymous mode, lower rate limit",
            "requires_key": False,
            "improves_with_key": True,
        },
        "ai": {
            "label": "AI summary",
            "status": "enabled" if ai_key and ai_model else "unavailable",
            "detail": (
                f"Env configured: {ai_model}"
                if ai_key and ai_model
                else "Optional. Add env vars or paste a session-only key in the UI."
            ),
            "base_url": ai_base,
            "requires_key": True,
        },
        "locality": {
            "label": "Local data",
            "status": "local",
            "detail": "Reports and reviewer decisions stay on this machine unless a live source or AI summary is invoked.",
            "requires_key": False,
        },
    }


@dataclass
class RunSnapshot:
    status: str = "idle"
    preset_id: str = ""
    current_source: str = ""
    started_at: str = ""
    completed_at: str = ""
    report_path: str = ""
    progress: int = 0
    logs: list[str] | None = None
    errors: list[str] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "preset_id": self.preset_id,
            "current_source": self.current_source,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "report_path": self.report_path,
            "progress": self.progress,
            "logs": self.logs or [],
            "errors": self.errors or [],
        }


class DiscoveryRuntime:
    def __init__(self, session: ReportSession, *, reports_dir: Path, state_db: Path):
        self.session = session
        self.reports_dir = reports_dir
        self.state_db = state_db
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._run = RunSnapshot(status="idle", report_path=str(session.report_path), logs=[], errors=[])

    def run_dict(self) -> dict[str, Any]:
        with self._lock:
            return self._run.as_dict()

    def _set_run(self, **updates: Any) -> None:
        with self._lock:
            for key, value in updates.items():
                setattr(self._run, key, value)

    def _log(self, message: str) -> None:
        with self._lock:
            logs = list(self._run.logs or [])
            logs.append(f"{_now_iso()} {message}")
            self._run.logs = logs[-80:]

    def _error(self, message: str) -> None:
        with self._lock:
            errors = list(self._run.errors or [])
            errors.append(message)
            self._run.errors = errors[-20:]
        self._log(f"ERROR: {message}")

    def start(self, preset_id: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        options = options or {}
        preset_ids = {p["id"] for p in PRESETS}
        if preset_id not in preset_ids:
            raise ValueError("Unknown preset.")
        with self._lock:
            if self._run.status == "running":
                raise RuntimeError("A discovery run is already active.")
            self._run = RunSnapshot(
                status="running",
                preset_id=preset_id,
                current_source="starting",
                started_at=_now_iso(),
                completed_at="",
                report_path=str(self.session.report_path),
                progress=2,
                logs=[],
                errors=[],
            )
            self._thread = threading.Thread(target=self._run_worker, args=(preset_id, options), daemon=True)
            self._thread.start()
            return self._run.as_dict()

    def _run_worker(self, preset_id: str, options: dict[str, Any]) -> None:
        try:
            if preset_id == "quick_demo":
                self._log("Loading checked-in sample report.")
                session = ReportSession.load(DEFAULT_SAMPLE_REPORT)
                with self._lock:
                    self.session = session
                self._set_run(
                    status="completed",
                    current_source="sample",
                    completed_at=_now_iso(),
                    report_path=str(DEFAULT_SAMPLE_REPORT),
                    progress=100,
                )
                self._log("Sample report ready.")
                return
            report_path = run_discovery_preset(
                preset_id,
                options,
                self._log,
                self._error,
                self._set_run,
                reports_dir=self.reports_dir,
                state_db=self.state_db,
            )
            session = ReportSession.load(report_path)
            with self._lock:
                self.session = session
            final_status = "partial_failure" if self._run.errors else "completed"
            self._set_run(
                status=final_status,
                current_source="complete",
                completed_at=_now_iso(),
                report_path=str(report_path),
                progress=100,
            )
            self._log(f"Run loaded into review queue: {report_path}")
        except Exception as exc:  # pragma: no cover - safety net for background worker
            self._error(str(exc))
            self._log(traceback.format_exc(limit=4))
            self._set_run(status="failed", current_source="failed", completed_at=_now_iso(), progress=100)


def _default_feed_url() -> str:
    feeds = load_allowlist(DEFAULT_ALLOWLIST)
    if not feeds:
        raise RuntimeError("No RSS feeds configured in allowlist.")
    return feeds[0]


def _ingest_rss(feed_url: str, *, allow_custom_feed: bool) -> list[dict[str, Any]]:
    if allow_custom_feed:
        xml = fetch_feed_xml(feed_url)
        return [entry_to_candidate(entry) for entry in parse_feed_entries(xml, feed_url)]
    return ingest_allowlisted_feed(feed_url, DEFAULT_ALLOWLIST)


def _window(days: int) -> tuple[str, str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return (
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _load_bridge_entries() -> list[Any]:
    path = default_bridge_path()
    if path and Path(path).exists():
        return load_bridge(path)
    return []


def _report_path_for(preset_id: str, reports_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in preset_id)
    return reports_dir / f"gap_run_{stamp}_{safe}.json"


def run_discovery_preset(
    preset_id: str,
    options: dict[str, Any],
    log: Any,
    error: Any,
    set_run: Any,
    *,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    state_db: Path = DEFAULT_DISCOVERY_DB,
) -> Path:
    max_items = max(1, min(100, int(options.get("max_items") or 20)))
    fetch_pages = bool(options.get("fetch_pages", False))
    feed_url = str(options.get("feed_url") or _default_feed_url()).strip()
    allow_custom_feed = bool(options.get("allow_custom_feed"))
    source_order = next(p["sources"] for p in PRESETS if p["id"] == preset_id)
    candidates: list[dict[str, Any]] = []
    source_errors: list[str] = []

    for idx, source in enumerate(source_order, start=1):
        set_run(current_source=source, progress=5 + round(40 * (idx - 1) / max(1, len(source_order))))
        log(f"Processing source: {source}.")
        try:
            if source == "rss":
                rows = _ingest_rss(feed_url, allow_custom_feed=allow_custom_feed)
            elif source == "nvd":
                start, end = _window(14)
                rows = ingest_nvd_incremental(
                    lastmod_start=start,
                    lastmod_end=end,
                    results_per_page=int(options.get("nvd_results_per_page") or 100),
                    max_pages=int(options.get("nvd_max_pages") or 1),
                    keyword=str(options.get("nvd_keyword") or "machine learning"),
                    state_db=state_db,
                )
            elif source == "ghsa":
                updated_after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
                rows = ingest_ghsa_incremental(
                    updated_after=str(options.get("ghsa_updated_after") or updated_after),
                    max_pages=int(options.get("ghsa_max_pages") or 1),
                    per_page=int(options.get("ghsa_per_page") or 100),
                    severity=str(options.get("ghsa_severity") or "high"),
                )
            else:
                rows = []
            rows = rows[:max_items]
            candidates.extend(rows)
            log(f"{source.upper()} produced {len(rows)} candidate(s).")
        except Exception as exc:
            msg = f"{source.upper()} failed: {exc}"
            source_errors.append(msg)
            error(msg)

    if not candidates:
        raise RuntimeError("No candidates were produced. " + ("; ".join(source_errors) if source_errors else ""))

    set_run(current_source="coverage", progress=52)
    log("Loading bundled AIDEFEND framework snapshot.")
    records = flatten_techniques(load_data_json(DEFAULT_DATA_JSON))
    index = BM25Index([record.search_text() for record in records])
    bridges = _load_bridge_entries()
    hosts = load_host_allowlist(DEFAULT_PAGE_ALLOWLIST)

    set_run(current_source="normalization", progress=64)
    for candidate in candidates:
        enrich_candidate(
            candidate,
            fetch_pages=fetch_pages,
            host_allowlist=hosts,
            fetch_timeout_s=12.0,
        )

    set_run(current_source="gap scoring", progress=76)
    reports = [
        build_gap_report(
            candidate,
            records,
            index,
            top_k=int(options.get("top_k") or 5),
            gap_bm25_max=float(options.get("gap_bm25_max") or 8.0),
            bridges=bridges,
        )
        for candidate in candidates
    ]

    set_run(current_source="local persistence", progress=88)
    reports_dir.mkdir(parents=True, exist_ok=True)
    append_jsonl(DEFAULT_CANDIDATES_OUT, candidates)
    run_params = {
        "preset_id": preset_id,
        "sources": source_order,
        "max_items": max_items,
        "fetch_pages": fetch_pages,
        "feed_url": feed_url if "rss" in source_order else "",
    }
    run_id = record_run(state_db, source=preset_id, params=run_params)
    for candidate in candidates:
        try:
            upsert_candidate(state_db, candidate, run_id=run_id)
        except ValueError:
            continue
    for report in reports:
        record_gap_report(state_db, run_id=run_id, gap_report=report)

    report_path = _report_path_for(preset_id, reports_dir)
    payload = {
        "generated_at": _now_iso(),
        "data_json": str(DEFAULT_DATA_JSON.resolve()),
        "source": preset_id,
        "sources": source_order,
        "feed_url": feed_url if "rss" in source_order else None,
        "technique_records": len(records),
        "candidates": candidates,
        "gap_reports": reports,
        "params": {
            **run_params,
            "top_k": int(options.get("top_k") or 5),
            "gap_bm25_max": float(options.get("gap_bm25_max") or 8.0),
            "partial_failures": source_errors,
        },
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"Wrote report: {report_path}")
    return report_path


def plain_gap_reason(gap_reason: Any) -> str:
    raw = str(gap_reason or "").strip()
    if not raw or raw == "missing":
        return "The backend did not return a specific gap signal. Review the evidence and nearest techniques manually."
    translations: list[str] = []
    for part in raw.split(";"):
        reason = part.strip()
        if not reason:
            continue
        if reason == "not_gap":
            translations.append("The nearest AIDEFEND matches look strong enough that this may already be covered.")
        elif reason.startswith("max_bm25_below_threshold"):
            translations.append("The closest AIDEFEND match was weak, so this may need review as a coverage gap.")
        elif reason == "threat_ids_in_text_but_no_framework_line_overlap":
            translations.append(
                "The source mentions framework-style threat identifiers that were not found in current AIDEFEND mappings."
            )
        else:
            translations.append("The backend raised an unmapped gap signal that needs reviewer inspection.")
    return " ".join(translations) or (
        "The backend did not return a specific gap signal. Review the evidence and nearest techniques manually."
    )


def deterministic_summary(detail: dict[str, Any]) -> str:
    evidence = detail["sections"]["evidence"]
    prov = detail["sections"]["provenance"]
    gap_summary = plain_gap_reason(prov.get("gap_reason"))
    return "\n".join(
        [
            f"What happened: {detail['sections']['what_this_is']}",
            f"Why it matters: {detail['sections']['why_care']}",
            f"How AIDEFEND appears to cover it: {detail['sections']['coverage_assessment']}",
            f"What may be missing: {gap_summary}",
            f"Suggested reviewer action: {detail['recommended_action']}",
            f"Evidence: CVE={_join_text(evidence['identifiers']['cves'])}; GHSA={_join_text(evidence['identifiers']['ghsas'])}; CWE={_join_text(evidence['identifiers']['cwes'])}; URLs={_join_text(evidence['source_urls'])}",
        ]
    )


def _compact_ai_context(detail: dict[str, Any]) -> dict[str, Any]:
    evidence = detail["sections"]["evidence"]
    prov = detail["sections"]["provenance"]
    nearest = detail["sections"]["similar_techniques"][:3]
    return {
        "title": detail["title"],
        "source_type": prov["source_type"],
        "source_id": prov["source_id"],
        "identifiers": evidence["identifiers"],
        "short_summary": export_review_digest._truncate(detail["sections"]["what_this_is"], 900),
        "severity": detail["severity"],
        "package_or_ecosystem": detail["ecosystem"] or evidence["packages"][:5],
        "nearest_aidefend_comparison": [
            {
                "id": item["id"],
                "bm25_score": item["bm25_score"],
                "lexical_overlap": item["lexical_overlap"][:8],
                "coverage_note": item["coverage_note"],
            }
            for item in nearest
        ],
        "gap_reason": prov["gap_reason"],
        "bridge_rationales": evidence["bridge_rationales"][:5],
        "source_urls": evidence["source_urls"][:5],
    }


def ai_summary(detail: dict[str, Any], request_data: dict[str, Any]) -> dict[str, Any]:
    fallback = deterministic_summary(detail)
    provider = str(request_data.get("provider") or os.environ.get("AI_SUMMARY_PROVIDER") or "openrouter").strip()
    base_url = str(
        request_data.get("base_url")
        or os.environ.get("AI_SUMMARY_BASE_URL")
        or ("https://openrouter.ai/api/v1" if provider == "openrouter" else "")
    ).rstrip("/")
    api_key = str(request_data.get("api_key") or os.environ.get("AI_SUMMARY_API_KEY") or "").strip()
    model = str(request_data.get("model") or os.environ.get("AI_SUMMARY_MODEL") or "").strip()
    if not api_key or not base_url or not model:
        return {
            "status": "unavailable",
            "summary": fallback,
            "fallback_summary": fallback,
            "fallback_used": True,
            "error": "AI summary is not configured. Using deterministic summary.",
        }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write concise security-review briefings. Do not claim candidates are approved "
                    "AIDEFEND truth. Use only the compact structured context."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": (
                            "Return concise readable bullets with these headings: What happened, Why it matters, "
                            "How AIDEFEND appears to cover it, What may be missing, Suggested reviewer action."
                        ),
                        "candidate_context": _compact_ai_context(detail),
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 550,
    }
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://127.0.0.1",
                "X-Title": "AIDEFEND Discovery local demo",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            response = json.loads(resp.read().decode("utf-8"))
        content = (((response.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("AI provider returned an empty summary.")
        return {
            "status": "ok",
            "summary": content,
            "fallback_summary": fallback,
            "fallback_used": False,
            "error": "",
        }
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, RuntimeError) as exc:
        return {
            "status": "failed",
            "summary": fallback,
            "fallback_summary": fallback,
            "fallback_used": True,
            "error": f"AI failed, using deterministic summary: {exc}",
        }


class ReviewConsoleHandler(SimpleHTTPRequestHandler):
    runtime: DiscoveryRuntime
    store: ReviewStore
    static_dir: Path

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(self.static_dir), **kwargs)

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, *, filename: str, content_type: str) -> None:
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            session = self.runtime.session
            self._send_json(
                {
                    "report_path": str(session.report_path),
                    "report_id": session.report_id,
                    "generated_at": session.payload.get("generated_at"),
                    "source": session.payload.get("source") or session.payload.get("feed_url"),
                    "candidate_count": len(session.rows),
                    "reviewed_count": reviewed_count_for_session(session, self.store),
                    "presets": PRESETS,
                    "source_health": source_health(),
                    "run_lifecycle": self.runtime.run_dict(),
                    "trust_posture": [
                        "Candidates are review hypotheses, not approved AIDEFEND truth.",
                        "Reviewer decision is separate from backend recommendation.",
                        "Data stays local unless a live source or AI summary is explicitly invoked.",
                    ],
                }
            )
            return
        if parsed.path == "/api/source-health":
            self._send_json(source_health())
            return
        if parsed.path == "/api/presets":
            self._send_json({"presets": PRESETS})
            return
        if parsed.path == "/api/candidates":
            self._send_json({"candidates": filtered_rows(self.runtime.session, self.store, parse_qs(parsed.query))})
            return
        if parsed.path.startswith("/api/candidates/"):
            key = unquote(parsed.path.rsplit("/", 1)[-1])
            row = self.runtime.session.find_row(key)
            if not row:
                self._send_json({"error": "Candidate not found."}, 404)
                return
            review = self.store.get(candidate_key(row.candidate, self.runtime.session.report_id))
            self._send_json(row_detail(row, self.runtime.session.report_id, review))
            return
        if parsed.path == "/api/reviewed":
            params = {"tab": ["reviewed"]}
            self._send_json({"candidates": filtered_rows(self.runtime.session, self.store, params)})
            return
        if parsed.path == "/api/export/markdown":
            self._send_text(
                export_review_digest.render_digest(
                    self.runtime.session.payload,
                    input_report=self.runtime.session.report_path,
                    top_n=max(10, len(self.runtime.session.rows)),
                ),
                filename="aidefend-discovery-digest.md",
                content_type="text/markdown; charset=utf-8",
            )
            return
        if parsed.path == "/api/export/csv":
            self._send_text(
                export_candidates_csv(self.runtime.session, self.store),
                filename="aidefend-discovery-candidates.csv",
                content_type="text/csv; charset=utf-8",
            )
            return
        if parsed.path == "/api/export/reviewed-markdown":
            self._send_text(
                export_reviewed_markdown(self.runtime.session, self.store),
                filename="aidefend-reviewed-candidates.md",
                content_type="text/markdown; charset=utf-8",
            )
            return
        if parsed.path == "/api/export/reviewed-csv":
            self._send_text(
                export_reviewed_csv(self.runtime.session, self.store),
                filename="aidefend-reviewed-candidates.csv",
                content_type="text/csv; charset=utf-8",
            )
            return
        if parsed.path == "/api/export/json":
            self._send_text(
                export_session_json(self.runtime.session, self.store),
                filename="aidefend-discovery-run.json",
                content_type="application/json; charset=utf-8",
            )
            return
        if parsed.path == "/api/export/action-packet":
            key = parse_qs(parsed.query).get("candidate_key", [""])[0]
            if not key:
                self._send_json({"error": "candidate_key is required."}, 400)
                return
            try:
                packet = export_action_packet(self.runtime.session, self.store, key)
            except KeyError as exc:
                self._send_json({"error": str(exc)}, 404)
                return
            self._send_text(
                packet,
                filename="aidefend-action-packet.md",
                content_type="text/markdown; charset=utf-8",
            )
            return
        if parsed.path == "/" and not (self.static_dir / "index.html").exists():
            self._send_json({"error": "Frontend build not found. Run npm install && npm run build in review_console."}, 503)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/runs":
            length = int(self.headers.get("Content-Length", "0") or 0)
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                run = self.runtime.start(_text(data.get("preset_id") or "quick_demo"), data.get("options") or {})
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, 409)
                return
            except (json.JSONDecodeError, ValueError) as exc:
                self._send_json({"error": str(exc)}, 400)
                return
            self._send_json({"run_lifecycle": run}, 202)
            return
        if parsed.path.startswith("/api/candidates/") and parsed.path.endswith("/ai-summary"):
            key = unquote(parsed.path.split("/")[-2])
            row = self.runtime.session.find_row(key)
            if not row:
                self._send_json({"error": "Candidate not found."}, 404)
                return
            length = int(self.headers.get("Content-Length", "0") or 0)
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                self._send_json({"error": str(exc)}, 400)
                return
            review = self.store.get(candidate_key(row.candidate, self.runtime.session.report_id))
            detail = row_detail(row, self.runtime.session.report_id, review)
            self._send_json(ai_summary(detail, data))
            return
        if not parsed.path.startswith("/api/candidates/") or not parsed.path.endswith("/review"):
            self._send_json({"error": "Not found."}, 404)
            return
        key = unquote(parsed.path.split("/")[-2])
        row = self.runtime.session.find_row(key)
        if not row:
            self._send_json({"error": "Candidate not found."}, 404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            saved = self.store.save(row, self.runtime.session.report_id, data)
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        self._send_json({"review": saved})


def make_handler(runtime: DiscoveryRuntime, store: ReviewStore, static_dir: Path) -> type[ReviewConsoleHandler]:
    class BoundReviewConsoleHandler(ReviewConsoleHandler):
        pass

    BoundReviewConsoleHandler.runtime = runtime
    BoundReviewConsoleHandler.store = store
    BoundReviewConsoleHandler.static_dir = static_dir
    return BoundReviewConsoleHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AIDEFEND Discovery review console API.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--static-dir", type=Path, default=DEFAULT_STATIC_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--state-db", type=Path, default=DEFAULT_DISCOVERY_DB)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if not args.report.exists():
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 1
    session = ReportSession.load(args.report)
    store = ReviewStore(args.db)
    runtime = DiscoveryRuntime(session, reports_dir=args.reports_dir, state_db=args.state_db)
    handler = make_handler(runtime, store, args.static_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"review-console running at http://{args.host}:{args.port}", file=sys.stderr)
    print(f"report={args.report} db={args.db}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
