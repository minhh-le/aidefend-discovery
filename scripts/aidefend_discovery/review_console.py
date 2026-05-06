"""Local API and sqlite review store for the AIDEFEND Discovery review console."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
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
DEFAULT_REPORT = ROOT / "reports" / "gap_run_20260505.json"
DEFAULT_DB = ROOT / "lab" / "aidefend_discovery" / "review_console.db"
DEFAULT_STATIC_DIR = ROOT / "review_console" / "dist"

REVIEW_DECISIONS = {
    "promote": "Promote",
    "merge": "Merge Into Existing",
    "reject": "Reject",
    "needs_evidence": "Needs Evidence",
    "monitor": "Monitor",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


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
        if min_cov and row.coverage_score < int(min_cov):
            continue
        if max_cov and row.coverage_score > int(max_cov):
            continue
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


class ReviewConsoleHandler(SimpleHTTPRequestHandler):
    session: ReportSession
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
            reviewed = self.store.reviewed_keys()
            self._send_json(
                {
                    "report_path": str(self.session.report_path),
                    "report_id": self.session.report_id,
                    "generated_at": self.session.payload.get("generated_at"),
                    "source": self.session.payload.get("source") or self.session.payload.get("feed_url"),
                    "candidate_count": len(self.session.rows),
                    "reviewed_count": len(reviewed),
                }
            )
            return
        if parsed.path == "/api/candidates":
            self._send_json({"candidates": filtered_rows(self.session, self.store, parse_qs(parsed.query))})
            return
        if parsed.path.startswith("/api/candidates/"):
            key = unquote(parsed.path.rsplit("/", 1)[-1])
            row = self.session.find_row(key)
            if not row:
                self._send_json({"error": "Candidate not found."}, 404)
                return
            review = self.store.get(candidate_key(row.candidate, self.session.report_id))
            self._send_json(row_detail(row, self.session.report_id, review))
            return
        if parsed.path == "/api/reviewed":
            params = {"tab": ["reviewed"]}
            self._send_json({"candidates": filtered_rows(self.session, self.store, params)})
            return
        if parsed.path == "/api/export/markdown":
            self._send_text(
                export_reviewed_markdown(self.session, self.store),
                filename="aidefend-reviewed-candidates.md",
                content_type="text/markdown; charset=utf-8",
            )
            return
        if parsed.path == "/api/export/csv":
            self._send_text(
                export_reviewed_csv(self.session, self.store),
                filename="aidefend-reviewed-candidates.csv",
                content_type="text/csv; charset=utf-8",
            )
            return
        if parsed.path == "/" and not (self.static_dir / "index.html").exists():
            self._send_json({"error": "Frontend build not found. Run npm install && npm run build in review_console."}, 503)
            return
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/candidates/") or not parsed.path.endswith("/review"):
            self._send_json({"error": "Not found."}, 404)
            return
        key = unquote(parsed.path.split("/")[-2])
        row = self.session.find_row(key)
        if not row:
            self._send_json({"error": "Candidate not found."}, 404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            saved = self.store.save(row, self.session.report_id, data)
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json({"error": str(exc)}, 400)
            return
        self._send_json({"review": saved})


def make_handler(session: ReportSession, store: ReviewStore, static_dir: Path) -> type[ReviewConsoleHandler]:
    class BoundReviewConsoleHandler(ReviewConsoleHandler):
        pass

    BoundReviewConsoleHandler.session = session
    BoundReviewConsoleHandler.store = store
    BoundReviewConsoleHandler.static_dir = static_dir
    return BoundReviewConsoleHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local AIDEFEND Discovery review console API.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--static-dir", type=Path, default=DEFAULT_STATIC_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if not args.report.exists():
        print(f"ERROR: report not found: {args.report}", file=sys.stderr)
        return 1
    session = ReportSession.load(args.report)
    store = ReviewStore(args.db)
    handler = make_handler(session, store, args.static_dir)
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
