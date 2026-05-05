"""GitHub global security advisories (GHSA) ingestion helpers.

Mirrors the NVD pattern: query builder + paginated fetch + normalize-to-candidate.
Auth via env var `GH_PAT_FOR_GHSA` (preferred) or `GITHUB_TOKEN` (fallback).
Anonymous calls are subject to GitHub's 60 req/hr limit and are not recommended.

Endpoint: https://api.github.com/advisories  (REST API; returns reviewed and
unreviewed global advisories). We default to `type=reviewed` for signal quality.

Pagination: GitHub uses opaque cursors. The Link header carries `rel="next"`
URLs with `after=<token>`. We parse and follow them up to `max_pages`.

Cursor: stored under `connector_state.ghsa_updated_after` as ISO 8601 UTC.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

GHSA_API_URL = "https://api.github.com/advisories"
GHSA_USER_AGENT = (
    "aidefend-discovery/0.3 "
    "(+https://github.com/minhh-le/aidefend-discovery; research prototype)"
)
GHSA_RETRY_STATUSES = frozenset({403, 429, 500, 502, 503, 504})
GHSA_MAX_RETRIES = 5
GHSA_BACKOFF_BASE_S = 1.5
GHSA_BACKOFF_CAP_S = 60.0
GHSA_DEFAULT_PER_PAGE = 100
GHSA_DEFAULT_TYPE = "reviewed"


def _ghsa_token() -> str | None:
    """Prefer the dedicated env var, fall back to GITHUB_TOKEN."""
    for env_name in ("GH_PAT_FOR_GHSA", "GITHUB_TOKEN"):
        v = os.environ.get(env_name)
        if v and v.strip():
            return v.strip()
    return None


def _backoff_seconds(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(GHSA_BACKOFF_CAP_S, max(0.0, float(retry_after.strip())))
        except ValueError:
            pass
    base = GHSA_BACKOFF_BASE_S * (2 ** max(0, attempt))
    jitter = random.uniform(0, base * 0.25)
    return min(GHSA_BACKOFF_CAP_S, base + jitter)


def build_ghsa_query(
    *,
    updated_after: str | None = None,
    advisory_type: str = GHSA_DEFAULT_TYPE,
    per_page: int = GHSA_DEFAULT_PER_PAGE,
    severity: str | None = None,
    cwes: str | None = None,
) -> dict[str, str]:
    """Build the initial query (page 1). Subsequent pages use the Link header."""
    q: dict[str, str] = {
        "type": advisory_type,
        "per_page": str(min(100, max(1, per_page))),
        "sort": "updated",
        "direction": "asc",  # asc so we walk forward in time deterministically
    }
    if updated_after:
        # GitHub accepts comparator-prefixed dates: ">2024-01-01"
        q["updated"] = f">{updated_after}"
    if severity:
        q["severity"] = severity
    if cwes:
        q["cwes"] = cwes
    return q


_LINK_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def _next_url(link_header: str | None) -> str | None:
    if not link_header:
        return None
    m = _LINK_NEXT_RE.search(link_header)
    return m.group(1) if m else None


def fetch_ghsa_page(
    url_or_query: str | dict[str, str],
    timeout_s: float = 30.0,
    *,
    sleep_fn: Callable[[float], None] | None = None,
    token: "str | None" = None,  # [REDACTED] — pulled from GH_PAT_FOR_GHSA env at call time
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch one GHSA page; return (items, next_url).

    Pass a dict for the first page (built via build_ghsa_query) or the
    full URL from the Link header for follow-up pages.
    """
    sleeper = sleep_fn or time.sleep
    tok = token if token is not None else _ghsa_token()

    if isinstance(url_or_query, dict):
        url = f"{GHSA_API_URL}?{urllib.parse.urlencode(url_or_query)}"
    else:
        url = url_or_query

    headers = {
        "User-Agent": GHSA_USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if tok:
        headers["Authorization"] = f"Bearer {tok}"

    last_exc: Exception | None = None
    for attempt in range(GHSA_MAX_RETRIES + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read()
                link = resp.headers.get("Link")
            items = json.loads(body.decode("utf-8"))
            return items, _next_url(link)
        except urllib.error.HTTPError as e:
            last_exc = e
            if e.code in GHSA_RETRY_STATUSES and attempt < GHSA_MAX_RETRIES:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                sleeper(_backoff_seconds(attempt, retry_after))
                continue
            raise
        except urllib.error.URLError as e:
            last_exc = e
            if attempt < GHSA_MAX_RETRIES:
                sleeper(_backoff_seconds(attempt, None))
                continue
            raise
    raise RuntimeError(f"GHSA fetch exhausted retries: {last_exc!r}")


def _extract_cwes(adv: dict[str, Any]) -> list[str]:
    out: set[str] = set()
    for cwe in adv.get("cwes") or []:
        cid = str(cwe.get("cwe_id", "")).strip().upper()
        if cid.startswith("CWE-"):
            out.add(cid)
    return sorted(out)


def _extract_version_constraints(adv: dict[str, Any]) -> list[str]:
    """Pull vulnerable_version_range + patched_versions per advised package."""
    out: list[str] = []
    for v in adv.get("vulnerabilities") or []:
        vrange = str(v.get("vulnerable_version_range", "")).strip()
        if vrange:
            out.append(f"vulnerable:{vrange}")
        for fix in v.get("patched_versions") or []:
            patch = str(fix).strip()
            if patch:
                out.append(f"patched:{patch}")
    # de-dup preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        if s in seen:
            continue
        seen.add(s)
        uniq.append(s)
    return uniq


def _extract_affected_packages(adv: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in adv.get("vulnerabilities") or []:
        pkg = v.get("package") or {}
        eco = str(pkg.get("ecosystem", "")).strip()
        name = str(pkg.get("name", "")).strip()
        if eco and name:
            key = f"{eco}:{name}"
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def _description(adv: dict[str, Any]) -> str:
    summary = str(adv.get("summary", "")).strip()
    description = str(adv.get("description", "")).strip()
    if summary and description:
        return f"{summary}\n\n{description}"
    return summary or description


def ghsa_to_candidate(adv: dict[str, Any], retrieved_at: str | None = None) -> dict[str, Any]:
    """Normalize a single GHSA advisory dict to CandidateFinding shape."""
    ghsa_id = str(adv.get("ghsa_id", "")).strip()
    cve_id = str(adv.get("cve_id") or "").strip().upper() if adv.get("cve_id") else ""
    description = _description(adv)
    cwes = _extract_cwes(adv)
    version_constraints = _extract_version_constraints(adv)
    packages = _extract_affected_packages(adv)
    refs = []
    for r in adv.get("references") or []:
        if isinstance(r, str) and r.strip():
            refs.append(r.strip())
        elif isinstance(r, dict):
            url = str(r.get("url", "")).strip()
            if url:
                refs.append(url)
    html_url = str(adv.get("html_url", "")).strip()
    if html_url and html_url not in refs:
        refs.insert(0, html_url)
    # de-dup
    seen_refs: set[str] = set()
    source_urls: list[str] = []
    for u in refs:
        if u in seen_refs:
            continue
        seen_refs.add(u)
        source_urls.append(u)

    now = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    canonical = json.dumps(
        {
            "ghsa_id": ghsa_id,
            "cve_id": cve_id,
            "summary": description,
            "cwes": cwes,
            "packages": packages,
            "source_urls": source_urls,
            "updated_at": adv.get("updated_at"),
        },
        sort_keys=True,
    ).encode("utf-8")
    raw_hash = hashlib.sha256(canonical).hexdigest()
    title = ghsa_id or (cve_id or "GitHub advisory")

    cves = [cve_id] if cve_id else []
    ghsas = [ghsa_id.lower()] if ghsa_id else []

    return {
        "id": f"candidate-ghsa-{raw_hash[:16]}",
        "status": "candidate",
        "title": title,
        "summary": description,
        "summary_raw": description,
        "source_urls": source_urls,
        "retrieved_at": now,
        "license_note": (
            "GitHub Security Advisory; CC BY 4.0 per GitHub Advisory Database; "
            "verify package vendor source for redistribution scope."
        ),
        "confidence": 0.75,
        "raw_hash": raw_hash,
        "feed_url": "ghsa_api",
        "source_type": "ghsa_api",
        "source_id": ghsa_id,
        "entities": {
            "cves": cves,
            "ghsas": ghsas,
            "cwes": cwes,
            "version_constraints": version_constraints,
        },
        "kev_flag": False,  # GHSA doesn't carry KEV; NVD enrichment can backfill
        "ghsa_severity": str(adv.get("severity", "")).lower() or None,
        "ghsa_packages": packages,
    }


def ingest_ghsa_incremental(
    *,
    updated_after: str | None,
    max_pages: int = 1,
    per_page: int = GHSA_DEFAULT_PER_PAGE,
    advisory_type: str = GHSA_DEFAULT_TYPE,
    severity: str | None = None,
    cwes: str | None = None,
    fetch_page_fn: Callable[..., tuple[list[dict[str, Any]], str | None]] | None = None,
    timeout_s: float = 30.0,
    page_delay_s: float = 0.0,
) -> list[dict[str, Any]]:
    """Walk GHSA pages from `updated_after` forward, up to `max_pages`."""
    fetcher = fetch_page_fn or fetch_ghsa_page
    out: list[dict[str, Any]] = []
    next_target: str | dict[str, str] = build_ghsa_query(
        updated_after=updated_after,
        advisory_type=advisory_type,
        per_page=per_page,
        severity=severity,
        cwes=cwes,
    )

    for _ in range(max(1, int(max_pages))):
        items, next_url = fetcher(next_target, timeout_s)
        for adv in items:
            out.append(ghsa_to_candidate(adv))
        if not next_url:
            break
        next_target = next_url
        if page_delay_s > 0:
            time.sleep(page_delay_s)

    return out
