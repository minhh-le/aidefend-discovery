"""NVD CVE 2.0 ingestion helpers for discovery candidates."""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_USER_AGENT = (
    "aidefend-discovery/0.2 "
    "(+https://github.com/minhh-le/aidefend-discovery; research prototype)"
)
MAX_NVD_WINDOW_DAYS = 120

# Retry policy: NVD signals rate-limit with HTTP 403 (not 429); transient with 5xx.
# Authenticated tier is 50 req / 30s; anonymous is 5 / 30s. Cap retries to fail loudly.
NVD_RETRY_STATUSES = frozenset({403, 429, 500, 502, 503, 504})
NVD_MAX_RETRIES = 5
NVD_BACKOFF_BASE_S = 1.5
NVD_BACKOFF_CAP_S = 60.0


def _nvd_api_key() -> str | None:
    """Read NVD_API_KEY at call time so tests can monkey-patch env."""
    key = os.environ.get("NVD_API_KEY")
    return key.strip() if key and key.strip() else None


def _backoff_seconds(attempt: int, retry_after: str | None) -> float:
    """Exponential with jitter, but obey Retry-After verbatim if the server set it."""
    if retry_after:
        try:
            return min(NVD_BACKOFF_CAP_S, max(0.0, float(retry_after.strip())))
        except ValueError:
            pass
    base = NVD_BACKOFF_BASE_S * (2 ** max(0, attempt))
    jitter = random.uniform(0, base * 0.25)
    return min(NVD_BACKOFF_CAP_S, base + jitter)


def _parse_iso8601(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build_nvd_query(
    *,
    lastmod_start: str | None,
    lastmod_end: str | None,
    start_index: int = 0,
    results_per_page: int = 2000,
    keyword: str | None = None,
) -> dict[str, Any]:
    if (lastmod_start and not lastmod_end) or (lastmod_end and not lastmod_start):
        raise ValueError("lastModStartDate and lastModEndDate must be provided together")
    if not lastmod_start or not lastmod_end:
        raise ValueError("lastModStartDate and lastModEndDate are required")

    start_dt = _parse_iso8601(lastmod_start)
    end_dt = _parse_iso8601(lastmod_end)
    if end_dt < start_dt:
        raise ValueError("lastModEndDate must be >= lastModStartDate")
    if (end_dt - start_dt).days > MAX_NVD_WINDOW_DAYS:
        raise ValueError("NVD last modified window must be <= 120 days")

    query: dict[str, Any] = {
        "lastModStartDate": start_dt.isoformat().replace("+00:00", "Z"),
        "lastModEndDate": end_dt.isoformat().replace("+00:00", "Z"),
        "startIndex": max(0, int(start_index)),
        "resultsPerPage": min(2000, max(1, int(results_per_page))),
    }
    if keyword:
        query["keywordSearch"] = keyword
    return query


def fetch_nvd_page(
    query: dict[str, Any],
    timeout_s: float = 30.0,
    *,
    sleep_fn: Callable[[float], None] | None = None,
    api_key: "str | None" = None,  # [REDACTED] — pulled from NVD_API_KEY env at call time
) -> dict[str, Any]:
    """Fetch one NVD page with auth + retry/backoff.

    Auth: pass `api_key` explicitly or set `NVD_API_KEY` in the env. Anonymous
    requests are rate-limited at 5/30s; authenticated at 50/30s. We retry on
    NVD_RETRY_STATUSES with exponential backoff + jitter, honoring `Retry-After`.
    """
    sleeper = sleep_fn or time.sleep
    key = api_key if api_key is not None else _nvd_api_key()
    headers = {"User-Agent": NVD_USER_AGENT}
    if key:
        headers["apiKey"] = key
    params = urllib.parse.urlencode(query)
    url = f"{NVD_CVE_API_URL}?{params}"

    last_exc: Exception | None = None
    for attempt in range(NVD_MAX_RETRIES + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                body = resp.read()
            return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_exc = e
            if e.code in NVD_RETRY_STATUSES and attempt < NVD_MAX_RETRIES:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                delay = _backoff_seconds(attempt, retry_after)
                sleeper(delay)
                continue
            raise
        except urllib.error.URLError as e:
            last_exc = e
            if attempt < NVD_MAX_RETRIES:
                sleeper(_backoff_seconds(attempt, None))
                continue
            raise
    # Should be unreachable, but be explicit.
    raise RuntimeError(f"NVD fetch exhausted retries: {last_exc!r}")


def _extract_cwe_ids(cve: dict[str, Any]) -> list[str]:
    cwes: set[str] = set()
    for weakness in cve.get("weaknesses", []):
        for desc in weakness.get("description", []):
            value = str(desc.get("value", "")).strip().upper()
            if value.startswith("CWE-"):
                cwes.add(value)
    return sorted(cwes)


def _extract_description(cve: dict[str, Any]) -> str:
    for desc in cve.get("descriptions", []):
        if str(desc.get("lang", "")).lower() == "en":
            value = str(desc.get("value", "")).strip()
            if value:
                return value
    if cve.get("descriptions"):
        return str(cve["descriptions"][0].get("value", "")).strip()
    return ""


def _extract_reference_urls(cve: dict[str, Any]) -> list[str]:
    """De-duplicated reference URLs preserving first-seen order."""
    seen: set[str] = set()
    urls: list[str] = []
    for ref in cve.get("references", []):
        url = str(ref.get("url", "")).strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def nvd_cve_to_candidate(item: dict[str, Any], retrieved_at: str | None = None) -> dict[str, Any]:
    cve = item.get("cve", {})
    cve_id = str(cve.get("id", "")).upper().strip()
    summary = _extract_description(cve)
    cwes = _extract_cwe_ids(cve)
    source_urls = _extract_reference_urls(cve)
    now = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    canonical = json.dumps(
        {
            "cve_id": cve_id,
            "summary": summary,
            "cwes": cwes,
            "source_urls": source_urls,
            "last_modified": cve.get("lastModified"),
        },
        sort_keys=True,
    ).encode("utf-8")
    raw_hash = hashlib.sha256(canonical).hexdigest()
    title = cve_id or "NVD advisory"

    return {
        "id": f"candidate-nvd-{raw_hash[:16]}",
        "status": "candidate",
        "title": title,
        "summary": summary,
        "summary_raw": summary,
        "source_urls": source_urls,
        "retrieved_at": now,
        "license_note": "NVD CVE API candidate; verify downstream redistribution policy.",
        "confidence": 0.7,
        "raw_hash": raw_hash,
        "feed_url": "nvd_api",
        "source_type": "nvd_api",
        "source_id": cve_id,
        "entities": {
            "cves": [cve_id] if cve_id else [],
            "cwes": cwes,
            "ghsas": [],
        },
        "kev_flag": bool(cve.get("cisaExploitAdd")),
    }


def iter_nvd_cves(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list(payload.get("vulnerabilities", []))


def ingest_nvd_incremental(
    *,
    lastmod_start: str | None,
    lastmod_end: str | None,
    results_per_page: int = 2000,
    max_pages: int = 1,
    keyword: str | None = None,
    state_db: Any = None,
    fetch_page_fn: Callable[[dict[str, Any], float], dict[str, Any]] | None = None,
    timeout_s: float = 30.0,
    page_delay_s: float = 0.0,
) -> list[dict[str, Any]]:
    del state_db  # integrated in a later task via state_store
    fetcher = fetch_page_fn or fetch_nvd_page
    out: list[dict[str, Any]] = []
    start_index = 0

    for _ in range(max(1, int(max_pages))):
        query = build_nvd_query(
            lastmod_start=lastmod_start,
            lastmod_end=lastmod_end,
            start_index=start_index,
            results_per_page=results_per_page,
            keyword=keyword,
        )
        payload = fetcher(query, timeout_s)
        vulns = iter_nvd_cves(payload)
        for item in vulns:
            out.append(nvd_cve_to_candidate(item))
        if len(vulns) < query["resultsPerPage"]:
            break
        start_index += query["resultsPerPage"]
        if page_delay_s > 0:
            time.sleep(page_delay_s)

    return out
