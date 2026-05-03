"""Fetch HTML and extract main text with Trafilatura; chunk for retrieval."""

from __future__ import annotations

import hashlib
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pathlib import Path

from aidefend_discovery.entities import entities_block, extract_entities, merge_entity_dicts
from aidefend_discovery.rss_ingest import USER_AGENT

DEFAULT_BODY_MAX_BYTES = 48 * 1024
DEFAULT_CHUNK_SIZE = 3500
DEFAULT_CHUNK_OVERLAP = 200


def normalize_hostname(host: str) -> str:
    h = (host or "").lower().strip()
    if ":" in h:
        h = h.split(":", 1)[0]
    if h.startswith("www."):
        h = h[4:]
    return h


def load_host_allowlist(path: str | Path) -> set[str]:
    p = Path(path)
    if not p.is_file():
        return set()
    hosts: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        hosts.add(normalize_hostname(s))
    return hosts


def host_allowed(url: str, allowed_hosts: set[str]) -> bool:
    if not allowed_hosts:
        return False
    try:
        host = normalize_hostname(urlparse(url).hostname or "")
    except ValueError:
        return False
    return host in allowed_hosts


def fetch_html(url: str, *, timeout_s: float = 25.0, max_bytes: int = 2_000_000) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    return raw.decode("utf-8", errors="replace")


def extract_main_text(html: str, url: str) -> str:
    import trafilatura

    text = trafilatura.extract(
        html,
        url=url,
        favor_recall=True,
        include_comments=False,
        include_tables=True,
    )
    if not text:
        return ""
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def truncate_bytes(s: str, max_bytes: int) -> tuple[str, bool]:
    if max_bytes <= 0:
        return "", True
    data = s.encode("utf-8")
    if len(data) <= max_bytes:
        return s, False
    cut = max_bytes
    while cut > 0 and (data[cut - 1] & 0xC0) == 0x80:
        cut -= 1
    return data[:cut].decode("utf-8", errors="ignore"), True


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
    source_url: str,
    max_chunks: int = 12,
) -> list[dict[str, Any]]:
    if not text.strip():
        return []
    t = text.strip()
    if len(t) <= chunk_size:
        return [
            {
                "index": 0,
                "text": t,
                "source_url": source_url,
                "char_start": 0,
                "char_end": len(t),
            }
        ]
    chunks: list[dict[str, Any]] = []
    start = 0
    idx = 0
    while start < len(t) and idx < max_chunks:
        end = min(len(t), start + chunk_size)
        piece = t[start:end]
        chunks.append(
            {
                "index": idx,
                "text": piece,
                "source_url": source_url,
                "char_start": start,
                "char_end": end,
            }
        )
        idx += 1
        if end >= len(t):
            break
        start = max(0, end - overlap)
    return chunks


def _canonical_hash(parts: list[str]) -> str:
    blob = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def enrich_candidate(
    candidate: dict[str, Any],
    *,
    fetch_pages: bool,
    host_allowlist: set[str],
    body_max_bytes: int = DEFAULT_BODY_MAX_BYTES,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    fetch_timeout_s: float = 25.0,
) -> dict[str, Any]:
    """
    Mutates and returns candidate: summary_raw, optional body_extracted,
    retrieval_chunks, body_retrieval, entities, raw_hash refresh.
    """
    title = str(candidate.get("title") or "")
    summary = str(candidate.get("summary") or "")
    candidate["summary_raw"] = candidate.get("summary_raw") or summary

    base_text = f"{title}\n\n{summary}".strip()
    # Preserve connector-supplied entities (NVD CWEs, GHSA package CWEs, etc.)
    # by merging text-extracted entities INTO whatever the connector populated.
    pre_entities = candidate.get("entities") or {}
    entities = merge_entity_dicts(pre_entities, extract_entities(base_text))
    body_extracted = ""
    body_fetch_error: str | None = None
    fetch_skipped_reason: str | None = None
    primary_url = (candidate.get("source_urls") or [None])[0]

    if fetch_pages and primary_url:
        if not host_allowed(primary_url, host_allowlist):
            fetch_skipped_reason = "host_not_in_page_fetch_allowlist"
        else:
            try:
                html = fetch_html(primary_url, timeout_s=fetch_timeout_s)
                body_extracted = extract_main_text(html, primary_url)
                if body_extracted:
                    entities = merge_entity_dicts(entities, extract_entities(body_extracted))
                else:
                    fetch_skipped_reason = "trafilatura_empty_extraction"
            except HTTPError as e:
                body_fetch_error = f"http_{e.code}"
                fetch_skipped_reason = body_fetch_error
            except URLError as e:
                body_fetch_error = f"url_{e.reason!s}"
                fetch_skipped_reason = body_fetch_error
            except OSError as e:
                body_fetch_error = str(e)[:200]
                fetch_skipped_reason = "io_error"
    elif fetch_pages and not primary_url:
        fetch_skipped_reason = "no_source_url"
    elif not fetch_pages:
        fetch_skipped_reason = "fetch_disabled"

    body_truncated = False
    if body_extracted:
        body_extracted, body_truncated = truncate_bytes(body_extracted, body_max_bytes)
    source_for_chunks = body_extracted if body_extracted.strip() else summary
    chunks = chunk_text(
        source_for_chunks,
        chunk_size=chunk_size,
        overlap=chunk_overlap,
        source_url=primary_url or "",
    )

    entity_line = entities_block(entities)
    chunk_queries: list[str] = []
    for ch in chunks:
        parts = [title.strip(), entity_line.strip(), str(ch.get("text") or "").strip()]
        chunk_queries.append("\n\n".join(p for p in parts if p))
    if not chunk_queries:
        chunk_queries.append(f"{title}\n\n{entity_line}\n\n{summary}".strip())

    candidate["body_extracted"] = body_extracted if body_extracted else None
    candidate["body_truncated"] = body_truncated
    candidate["body_extracted_bytes"] = len(body_extracted.encode("utf-8")) if body_extracted else 0
    candidate["body_fetch_error"] = body_fetch_error
    candidate["body_fetch_skipped_reason"] = fetch_skipped_reason
    candidate["entities"] = entities
    candidate["retrieval_chunks"] = chunks
    candidate["retrieval_chunk_queries"] = chunk_queries
    primary_body = (body_extracted or "").strip() or summary
    br_full = f"{title}\n\n{primary_body}".strip()
    body_retrieval, br_trunc = truncate_bytes(br_full, body_max_bytes)
    candidate["body_retrieval"] = body_retrieval
    candidate["body_retrieval_truncated"] = br_trunc

    h = _canonical_hash(
        [
            title,
            candidate["summary_raw"],
            body_extracted or "",
            entity_line,
            primary_url or "",
        ]
    )
    candidate["content_hash"] = h
    candidate["raw_hash"] = h
    candidate["id"] = f"candidate-rss-{h[:16]}"
    return candidate
