#!/usr/bin/env python3
"""Render a public-review Markdown digest from one gap_run_*.json report.

The digest is deterministic and uses only the single-run JSON report. It is
intended as the reviewer-facing surface for public testing while raw candidate
and gap-report provenance remains available in secondary sections.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_REPORT = ROOT / "tests" / "fixtures" / "sample_gap_run.json"

SEVERITY_BASE = {
    "critical": 100,
    "high": 85,
    "medium": 60,
    "low": 35,
    "unknown": 40,
    "": 40,
}
ACTION_PROMOTE = "Promote"
ACTION_MERGE = "Merge Into Existing"
ACTION_REJECT = "Reject"
ACTION_NEEDS_EVIDENCE = "Needs Evidence"
ACTION_MONITOR = "Monitor"

QUALITY_RAW_SOURCE_ITEM = "raw_source_item"
QUALITY_NORMALIZED_CANDIDATE = "normalized_candidate"
QUALITY_NEEDS_ENRICHMENT = "needs_enrichment"
QUALITY_REVIEW_READY = "review_ready"
QUALITY_LOW_SIGNAL = "low_signal"

QUALITY_LABELS = {
    QUALITY_RAW_SOURCE_ITEM: "Raw Source Item",
    QUALITY_NORMALIZED_CANDIDATE: "Normalized Candidate",
    QUALITY_NEEDS_ENRICHMENT: "Needs Enrichment",
    QUALITY_REVIEW_READY: "Review Ready",
    QUALITY_LOW_SIGNAL: "Low Signal",
}

ATTACK_NARRATIVE_TERMS = (
    "arbitrary file read",
    "arbitrary code",
    "broken access control",
    "bypass",
    "command injection",
    "code execution",
    "denial of service",
    "deserialization",
    "exfiltration",
    "exposes",
    "file read",
    "read files",
    "hijack",
    "injection",
    "malicious",
    "path traversal",
    "poison",
    "remote code",
    "resource exhaustion",
    "server-side request forgery",
    "spoof",
    "ssrf",
    "traversal",
    "traverse",
    "unauthenticated",
    "unauthorized",
    "untrusted",
    "vulnerability",
    "xss",
)

GENERIC_BRIEF_MARKERS = (
    "max_bm25",
    "gap_bm25",
    "coverage_ceiling",
    "security score includes",
    "severity basis",
    "deterministic boosts",
)


@dataclass(frozen=True)
class DigestRow:
    candidate: dict[str, Any]
    gap_report: dict[str, Any]
    gap_bm25_max: float | int | None
    coverage_ceiling: float | int | None
    coverage_score: int
    security_score: int
    recommended_action: str

    @property
    def candidate_id(self) -> str:
        return str(self.candidate.get("id") or self.gap_report.get("candidate_id") or "")

    @property
    def title(self) -> str:
        return str(self.candidate.get("title") or self.candidate_id or "Untitled candidate")


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _truncate(value: Any, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", _text(value)).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _md_escape(value: Any) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ").strip()


def _severity(candidate: dict[str, Any]) -> str:
    for key in ("severity", "ghsa_severity", "nvd_severity", "cvss_severity"):
        value = _text(candidate.get(key)).strip().lower()
        if value:
            return value
    return "unknown"


def _entities(candidate: dict[str, Any]) -> dict[str, list[Any]]:
    entities = candidate.get("entities") or {}
    if not isinstance(entities, dict):
        return {}
    return {str(k): _as_list(v) for k, v in entities.items()}


def _source_family(candidate: dict[str, Any]) -> str:
    source_type = _text(candidate.get("source_type")).lower()
    source_id = _text(candidate.get("source_id")).lower()
    feed_url = _text(candidate.get("feed_url")).lower()
    if "ghsa" in source_type or source_id.startswith("ghsa-") or "github.com/advisories" in feed_url:
        return "ghsa"
    if "nvd" in source_type or source_id.startswith("cve-") or "nvd.nist.gov" in feed_url:
        return "nvd"
    if source_type == "rss" or feed_url:
        return "rss"
    return "unknown"


def _has_identifier(candidate: dict[str, Any]) -> bool:
    entities = _entities(candidate)
    return bool(entities.get("cves") or entities.get("ghsas") or entities.get("cwes"))


def _has_cve(candidate: dict[str, Any]) -> bool:
    return bool(_entities(candidate).get("cves"))


def _has_ghsa(candidate: dict[str, Any]) -> bool:
    return bool(_entities(candidate).get("ghsas"))


def _has_cwe(candidate: dict[str, Any]) -> bool:
    return bool(_entities(candidate).get("cwes"))


def _has_package_or_version(candidate: dict[str, Any]) -> bool:
    entities = _entities(candidate)
    if entities.get("version_constraints"):
        return True
    for key in ("ghsa_packages", "packages", "affected_packages", "ecosystems"):
        if _as_list(candidate.get(key)):
            return True
    return False


def _is_reviewed_source(candidate: dict[str, Any]) -> bool:
    return _source_family(candidate) in {"ghsa", "nvd"}


def _has_advisory_reference(candidate: dict[str, Any]) -> bool:
    source_id = _text(candidate.get("source_id")).lower()
    urls = " ".join(_text(url).lower() for url in _as_list(candidate.get("source_urls")))
    return (
        source_id.startswith(("cve-", "ghsa-"))
        or "github.com/advisories/" in urls
        or "nvd.nist.gov/vuln/detail/" in urls
    )


def _has_source_detail(candidate: dict[str, Any]) -> bool:
    return bool(_as_list(candidate.get("source_urls")) or candidate.get("source_id"))


def _is_reject_signal(candidate: dict[str, Any]) -> bool:
    status = _text(candidate.get("status")).lower()
    reason = _text(candidate.get("rejected_reason") or candidate.get("rejection_reason")).lower()
    scope = _text(candidate.get("scope_status") or candidate.get("review_scope")).lower()
    if status == "rejected":
        return True
    return any(
        marker in reason or marker in scope
        for marker in ("out_of_scope", "out of scope", "duplicate", "false_positive", "not security", "not ai")
    )


def _has_mapping_evidence(gap_report: dict[str, Any]) -> bool:
    return bool(
        _as_list(gap_report.get("bridge_rationales"))
        or _as_list(gap_report.get("nearest_technique_ids"))
        or _as_list(gap_report.get("suggested_tactic_ids"))
    )


def _clean_summary_text(value: Any) -> str:
    text = _text(value)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first_meaningful_sentence(text: str, *, limit: int = 360) -> str:
    clean = _clean_summary_text(text)
    if not clean:
        return ""
    parts = [p.strip(" :-") for p in re.split(r"(?<=[.!?])\s+|\s{2,}", clean) if p.strip()]
    candidates = parts if parts else [clean]
    lower_terms = ATTACK_NARRATIVE_TERMS
    for part in candidates:
        lowered = part.lower()
        if len(part) >= 45 and any(term in lowered for term in lower_terms):
            return _truncate(part, limit)
    return _truncate(candidates[0], limit)


def _explicit_narrative(candidate: dict[str, Any], key: str) -> str:
    narrative = candidate.get("narrative") or candidate.get("brief") or {}
    if isinstance(narrative, dict):
        return _clean_summary_text(narrative.get(key) or "")
    return ""


def _what_happened(row: DigestRow) -> str:
    explicit = _explicit_narrative(row.candidate, "what_happened")
    if explicit:
        return _truncate(explicit, 520)
    summary = row.candidate.get("summary") or row.candidate.get("summary_raw") or ""
    return _first_meaningful_sentence(summary, limit=520) or "No attack or vulnerability narrative could be built from the source."


def _has_attack_narrative(row: DigestRow) -> bool:
    text = _what_happened(row).lower()
    if len(text) < 55:
        return False
    if any(marker in text for marker in GENERIC_BRIEF_MARKERS):
        return False
    return any(term in text for term in ATTACK_NARRATIVE_TERMS)


def _looks_like_release_note(candidate: dict[str, Any]) -> bool:
    title = _text(candidate.get("title"))
    summary = _clean_summary_text(candidate.get("summary") or candidate.get("summary_raw") or "")
    blob = f"{title} {summary}".lower()
    package_title = bool(re.search(r"\b[a-z0-9_.-]+==\d", title.lower()))
    release_markers = (
        "changes since",
        "release(",
        "chore(",
        "feat(",
        "fix(",
        "bump ",
        "merge remote-tracking",
    )
    return package_title or any(marker in blob for marker in release_markers)


def quality_status(row: DigestRow) -> str:
    c = row.candidate
    if not _text(c.get("id")) or not _text(c.get("title")):
        return QUALITY_RAW_SOURCE_ITEM
    if _is_reject_signal(c):
        return QUALITY_LOW_SIGNAL

    has_summary = bool(_text(c.get("summary") or c.get("summary_raw")).strip())
    if not has_summary:
        return QUALITY_RAW_SOURCE_ITEM

    has_identifier = _has_identifier(c)
    has_source = _has_source_detail(c)
    has_attack = _has_attack_narrative(row)
    is_reviewed_advisory = _is_reviewed_source(c)
    release_like = _looks_like_release_note(c)

    if is_reviewed_advisory and has_source and has_identifier and has_attack:
        return QUALITY_REVIEW_READY
    if has_identifier or _has_advisory_reference(c):
        return QUALITY_NEEDS_ENRICHMENT
    if release_like or (_source_family(c) == "rss" and _has_package_or_version(c)):
        return QUALITY_LOW_SIGNAL
    if has_attack:
        return QUALITY_NORMALIZED_CANDIDATE
    return QUALITY_LOW_SIGNAL


def quality_reason(row: DigestRow) -> str:
    status = quality_status(row)
    if status == QUALITY_REVIEW_READY:
        return "Advisory source, identifiers, evidence URL, and attack narrative are present."
    if status == QUALITY_NEEDS_ENRICHMENT:
        if _source_family(row.candidate) == "rss":
            return "Advisory identifiers were observed in a broad feed item, but the item needs advisory enrichment before review."
        return "The item has advisory signal, but the attack narrative or evidence is incomplete."
    if status == QUALITY_LOW_SIGNAL:
        if _looks_like_release_note(row.candidate):
            return "Broad release-note or package-version item without enough vulnerability narrative."
        return "Insufficient advisory signal for the default review queue."
    if status == QUALITY_RAW_SOURCE_ITEM:
        return "Source data is missing normalized candidate fields."
    return "Normalized but not enriched enough for the default review queue."


def _existing_coverage(row: DigestRow) -> str:
    explicit = _explicit_narrative(row.candidate, "existing_coverage")
    if explicit:
        return _truncate(explicit, 420)
    bridge = _as_list(row.gap_report.get("bridge_rationales"))
    nearest = _as_list(row.gap_report.get("nearest_technique_ids"))
    if bridge:
        nearest_text = f" Nearest AIDEFEND evidence: {_csv(nearest[:3])}." if nearest else ""
        return _truncate(f"Strongest existing coverage is the mapped defense family from the CWE bridge: {bridge[0]}{nearest_text}", 520)
    if nearest:
        return f"Strongest existing coverage appears to be {nearest[0]}, with nearby candidates {_csv(nearest[:3])}."
    return "No nearest AIDEFEND technique was reported, so existing coverage is unclear."


def _gap_assessment(row: DigestRow) -> str:
    explicit = _explicit_narrative(row.candidate, "gap_assessment")
    if explicit:
        return _truncate(explicit, 420)
    nearest = _csv(_as_list(row.gap_report.get("nearest_technique_ids"))[:3])
    if row.gap_report.get("is_gap") and row.coverage_score <= 40:
        return f"Likely gap: current lexical coverage is weak and the nearest evidence is limited to {nearest}."
    if row.coverage_score >= 60 and not row.gap_report.get("is_gap"):
        return f"Likely covered: current AIDEFEND neighbors are strong enough to review this as a merge into {nearest}."
    return f"Unclear: the item has security signal, but the nearest AIDEFEND comparison needs human review ({nearest})."


def _why_it_matters(row: DigestRow) -> str:
    explicit = _explicit_narrative(row.candidate, "why_it_matters")
    if explicit:
        return _truncate(explicit, 520)
    c = row.candidate
    what = _what_happened(row).lower()
    entities = _entities(c)
    cwes = " ".join(str(v) for v in entities.get("cwes", []))
    attack_text = f"{what} {cwes}".lower()
    if any(term in attack_text for term in ("command injection", "code execution", "cwe-78", "cwe-94", "deserialization", "cwe-502")):
        impact = "An attacker may be able to run code or cross a trust boundary through unsafe execution or object loading."
    elif any(term in attack_text for term in ("path traversal", "file read", "cwe-22", "cwe-200", "exposes", "exfiltration")):
        impact = "An attacker may be able to read or expose files, prompts, agent state, or other sensitive runtime data."
    elif any(term in attack_text for term in ("ssrf", "server-side request forgery", "cwe-918")):
        impact = "An attacker may be able to make a trusted service issue network requests to attacker-selected locations."
    elif any(term in attack_text for term in ("denial of service", "resource exhaustion", "cwe-400", "cwe-770")):
        impact = "An attacker may be able to exhaust compute, memory, or service capacity."
    elif any(term in attack_text for term in ("authorization", "authentication", "bypass", "unauthorized", "unauthenticated")):
        impact = "An attacker may be able to use protected functionality without the intended authorization checks."
    else:
        impact = "An attacker may be able to exploit the affected software in a way that changes confidentiality, integrity, or availability."
    return f"{impact} For AIDEFEND, this should be reviewed against the closest defense coverage before any promotion decision."


def narrative_sections(row: DigestRow) -> dict[str, str]:
    return {
        "what_happened": _what_happened(row),
        "why_it_matters": _why_it_matters(row),
        "existing_coverage": _existing_coverage(row),
        "gap_assessment": _gap_assessment(row),
    }


def quality_summary(rows: list[DigestRow]) -> dict[str, Any]:
    counts = Counter(quality_status(row) for row in rows)
    needs = (
        counts[QUALITY_NEEDS_ENRICHMENT]
        + counts[QUALITY_NORMALIZED_CANDIDATE]
        + counts[QUALITY_RAW_SOURCE_ITEM]
    )
    return {
        "ingested": len(rows),
        "review_ready": counts[QUALITY_REVIEW_READY],
        "needs_enrichment": needs,
        "low_signal": counts[QUALITY_LOW_SIGNAL],
        "status_counts": {key: counts[key] for key in QUALITY_LABELS},
    }


def coverage_score(gap_report: dict[str, Any], coverage_ceiling: float | int | None) -> int:
    """Return 0..100 coverage score relative to the strongest match in this report."""
    try:
        ceiling = float(coverage_ceiling or 0)
        max_bm25 = float(gap_report.get("max_bm25") or 0)
    except (TypeError, ValueError):
        return 0
    if ceiling <= 0 or max_bm25 <= 0:
        return 0
    return round(min(100, 100 * max_bm25 / ceiling))


def security_score(candidate: dict[str, Any]) -> int:
    """Return 0..100 security score from severity plus bounded evidence boosts."""
    score = SEVERITY_BASE.get(_severity(candidate), SEVERITY_BASE["unknown"])
    if _is_reviewed_source(candidate):
        score += 5
    if _has_cve(candidate):
        score += 5
    if _has_ghsa(candidate):
        score += 5
    if _has_cwe(candidate):
        score += 5
    if _has_package_or_version(candidate):
        score += 5
    return min(100, score)


def recommended_action(candidate: dict[str, Any], gap_report: dict[str, Any], cov_score: int, sec_score: int) -> str:
    """Return one of the public review action labels."""
    if _is_reject_signal(candidate):
        return ACTION_REJECT
    if not _has_source_detail(candidate) or not _has_identifier(candidate):
        return ACTION_NEEDS_EVIDENCE
    if cov_score <= 40 and sec_score >= 80 and gap_report.get("is_gap"):
        return ACTION_PROMOTE
    if cov_score >= 60 and sec_score >= 70:
        return ACTION_MERGE
    return ACTION_MONITOR


def _gap_threshold(payload: dict[str, Any]) -> float | None:
    params = payload.get("params") or {}
    if isinstance(params, dict):
        if "gap_bm25_max" in params:
            return params.get("gap_bm25_max")
    return payload.get("gap_bm25_max")


def build_rows(payload: dict[str, Any]) -> list[DigestRow]:
    threshold = _gap_threshold(payload)
    gap_reports = [g for g in _as_list(payload.get("gap_reports")) if isinstance(g, dict)]
    max_scores: list[float] = []
    for gap_report in gap_reports:
        try:
            max_scores.append(float(gap_report.get("max_bm25") or 0))
        except (TypeError, ValueError):
            continue
    coverage_ceiling = max(max_scores) if max_scores else None
    gap_by_id = {
        str(g.get("candidate_id")): g
        for g in gap_reports
        if isinstance(g, dict) and g.get("candidate_id")
    }
    rows: list[DigestRow] = []
    for candidate in _as_list(payload.get("candidates")):
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("id") or "")
        gap = gap_by_id.get(candidate_id, {})
        cov = coverage_score(gap, coverage_ceiling)
        sec = security_score(candidate)
        rows.append(
            DigestRow(
                candidate=candidate,
                gap_report=gap,
                gap_bm25_max=threshold,
                coverage_ceiling=coverage_ceiling,
                coverage_score=cov,
                security_score=sec,
                recommended_action=recommended_action(candidate, gap, cov, sec),
            )
        )
    return rows


def _rank_lowest_coverage(rows: list[DigestRow], top_n: int) -> list[DigestRow]:
    return sorted(rows, key=lambda r: (r.coverage_score, -r.security_score, r.title, r.candidate_id))[:top_n]


def _rank_highest_security(rows: list[DigestRow], top_n: int) -> list[DigestRow]:
    return sorted(rows, key=lambda r: (-r.security_score, r.coverage_score, r.title, r.candidate_id))[:top_n]


def _brief_rows(lowest: list[DigestRow], highest: list[DigestRow], top_n: int) -> list[DigestRow]:
    out: list[DigestRow] = []
    seen: set[str] = set()
    for row in lowest + highest:
        if row.candidate_id in seen:
            continue
        seen.add(row.candidate_id)
        out.append(row)
        if len(out) >= top_n:
            break
    return out


def _source_counts(rows: list[DigestRow]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        source = _text(row.candidate.get("source_type") or row.candidate.get("feed_url") or "unknown")
        counts[source or "unknown"] += 1
    return counts


def _table(rows: list[DigestRow], *, kind: str) -> list[str]:
    if kind == "coverage":
        lines = [
            "| Rank | Candidate | Coverage Score | Security Score | Recommended Action |",
            "| ---: | --- | ---: | ---: | --- |",
        ]
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"| {idx} | {_md_escape(row.title)} | {row.coverage_score}/100 | "
                f"{row.security_score}/100 | {row.recommended_action} |"
            )
        return lines
    lines = [
        "| Rank | Candidate | Security Score | Coverage Score | Recommended Action |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"| {idx} | {_md_escape(row.title)} | {row.security_score}/100 | "
            f"{row.coverage_score}/100 | {row.recommended_action} |"
        )
    return lines


def _csv(values: list[Any]) -> str:
    return ", ".join(_text(v) for v in values if _text(v)) or "None observed"


def _raw_score_details(row: DigestRow) -> str:
    return (
        f"max_bm25={row.gap_report.get('max_bm25', 'missing')}; "
        f"gap_bm25_max={row.gap_bm25_max if row.gap_bm25_max is not None else 'missing'}; "
        f"coverage_ceiling={row.coverage_ceiling if row.coverage_ceiling is not None else 'missing'}; "
        f"bm25_scores={_csv(_as_list(row.gap_report.get('bm25_scores')))}"
    )


def _render_brief(row: DigestRow) -> list[str]:
    c = row.candidate
    g = row.gap_report
    entities = _entities(c)
    narrative = narrative_sections(row)
    status = quality_status(row)
    lines = [
        f"### {_md_escape(row.title)}",
        "",
        f"- Candidate Quality: {QUALITY_LABELS.get(status, status)}",
        f"- Quality Reason: {quality_reason(row)}",
        f"- Coverage Score: {row.coverage_score}/100",
        f"- Security Score: {row.security_score}/100",
        f"- Recommended Action: {row.recommended_action}",
        "",
        "#### Reviewer Decision Checklist",
        "",
        "- [ ] Confirm this is AI/security relevant.",
        "- [ ] Confirm whether the nearest AIDEFEND techniques already cover the behavior.",
        "- [ ] Confirm whether source identifiers and affected package/version evidence are sufficient.",
        "- [ ] Record promote, merge, reject, needs-evidence, or monitor decision.",
        "",
        "#### What happened?",
        "",
        narrative["what_happened"],
        "",
        "#### Why does it matter?",
        "",
        narrative["why_it_matters"],
        "",
        "#### What does AIDEFEND already cover?",
        "",
        narrative["existing_coverage"],
        "",
        "#### Is this likely a gap?",
        "",
        narrative["gap_assessment"],
        "",
        "#### Evidence",
        "",
        f"- Identifiers: CVE={_csv(entities.get('cves', []))}; GHSA={_csv(entities.get('ghsas', []))}; CWE={_csv(entities.get('cwes', []))}",
        f"- Affected packages / versions: packages={_csv(_as_list(c.get('ghsa_packages') or c.get('packages')))}; versions={_csv(entities.get('version_constraints', []))}",
        f"- Source URLs: {_csv(_as_list(c.get('source_urls')))}",
        f"- Bridge rationales: {_csv(_as_list(g.get('bridge_rationales')))}",
        f"- Nearest technique IDs: {_csv(_as_list(g.get('nearest_technique_ids')))}",
        "",
        "#### Backend Provenance",
        "",
        f"- Candidate ID: {row.candidate_id}",
        f"- Source type: {_text(c.get('source_type') or c.get('feed_url') or 'unknown')}",
        f"- Source ID: {_text(c.get('source_id') or 'unknown')}",
        f"- Retrieved at: {_text(c.get('retrieved_at') or 'unknown')}",
        f"- Raw score details: {_raw_score_details(row)}",
        f"- Gap reason: {_text(g.get('gap_reason') or 'missing')}",
        f"- Producer confidence: {_text(c.get('confidence') or 'unknown')}",
        f"- License note: {_text(c.get('license_note') or 'unknown')}",
        "",
    ]
    return lines


def _why_care(row: DigestRow) -> str:
    return narrative_sections(row)["why_it_matters"]


def _coverage_assessment(row: DigestRow) -> str:
    return narrative_sections(row)["existing_coverage"]


def _security_assessment(row: DigestRow) -> str:
    return narrative_sections(row)["gap_assessment"]


def render_digest(payload: dict[str, Any], *, input_report: Path, top_n: int, generated_at: str | None = None) -> str:
    top_n = max(1, int(top_n))
    generated = (
        generated_at
        or _text(payload.get("generated_at"))
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    rows = build_rows(payload)
    summary = quality_summary(rows)
    review_ready = [row for row in rows if quality_status(row) == QUALITY_REVIEW_READY]
    ranking_pool = review_ready if review_ready else rows
    lowest = _rank_lowest_coverage(ranking_pool, top_n)
    highest = _rank_highest_security(ranking_pool, top_n)
    briefs = _brief_rows(lowest, highest, top_n)
    counts = _source_counts(rows)
    source_counts = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())) or "none"

    lines = [
        "# AIDEFEND Discovery Public Review Digest",
        "",
        "## Run Summary",
        "",
        f"- Candidates analyzed: {len(rows)}",
        f"- Review-ready candidates: {summary['review_ready']}",
        f"- Needs enrichment: {summary['needs_enrichment']}",
        f"- Low signal: {summary['low_signal']}",
        f"- Candidates shown in detail: {len(briefs)}",
        f"- Number in lowest coverage view: {len(lowest)}",
        f"- Number in highest severity view: {len(highest)}",
        f"- Source counts: {source_counts}",
        f"- Generated timestamp: {generated}",
        f"- Input report path: {input_report}",
        f"- Source: {_text(payload.get('source') or 'unknown')}",
        "",
        "## Lowest Coverage Candidates",
        "",
        *_table(lowest, kind="coverage"),
        "",
        "## Highest Severity Candidates",
        "",
        *_table(highest, kind="severity"),
        "",
        "## Candidate Briefs",
        "",
    ]
    for row in briefs:
        lines.extend(_render_brief(row))
    lines.extend(
        [
            "## Methodology / Provenance Appendix",
            "",
            "- Input source is one deterministic `gap_run_*.json` report, not sqlite backlog/history.",
            "- Coverage Score is `round(min(100, 100 * max_bm25 / strongest_max_bm25_in_report))`, preserving relative coverage within the run.",
            "- Security Score starts from advisory severity and adds bounded evidence boosts for reviewed source, CVE, GHSA, CWE, and package/version evidence.",
            "- Review-ready candidates require advisory evidence and a deterministic attack or vulnerability narrative.",
            "- Needs-enrichment and low-signal items remain in exports, but they are not the default review queue.",
            "- Recommended actions are deterministic reviewer triage labels. They are not upstream AIDEFEND truth.",
            "- Raw provenance remains in each candidate brief: source URL, source type, candidate ID, retrieved timestamp, identifiers, and raw score details.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, help="Path to reports/gap_run_YYYYMMDD.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / f"discovery_digest_{datetime.now(timezone.utc).strftime('%Y%m%d')}.md",
    )
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--sample", action="store_true", help="Load the checked-in sample report fixture")
    args = parser.parse_args(argv)

    report_path = SAMPLE_REPORT if args.sample else args.report
    if report_path is None:
        print("ERROR: --report is required unless --sample is used", file=sys.stderr)
        return 2
    if not report_path.exists():
        print(f"ERROR: report not found: {report_path}", file=sys.stderr)
        return 1

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    digest = render_digest(payload, input_report=report_path, top_n=args.top_n)
    args.output.write_text(digest, encoding="utf-8")
    print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
