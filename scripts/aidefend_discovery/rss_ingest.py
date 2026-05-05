"""Fetch allowlisted RSS or Atom feeds and emit CandidateFinding-shaped dicts."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

USER_AGENT = (
    "aidefend-discovery/0.1 "
    "(+https://github.com/minhh-le/aidefend-discovery; research prototype)"
)


def load_allowlist(path: Path) -> list[str]:
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _ensure_allowed(url: str, allowed: list[str]) -> None:
    if url not in allowed:
        raise ValueError(f"URL not in allowlist: {url}")


def fetch_feed_xml(url: str, timeout_s: float = 30.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return resp.read()


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _strip_ns(elem: ET.Element) -> None:
    """Strip namespaces for simpler matching."""
    elem.tag = _local_name(elem.tag)
    for c in list(elem):
        _strip_ns(c)


def parse_feed_entries(xml_bytes: bytes, feed_url: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    _strip_ns(root)
    tag = root.tag.lower()
    entries: list[dict[str, Any]] = []

    if tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return entries
        for item in channel.findall("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            pub_el = item.find("pubDate")
            title = (title_el.text or "").strip() if title_el is not None else ""
            link = (link_el.text or "").strip() if link_el is not None else ""
            desc = (desc_el.text or "").strip() if desc_el is not None else ""
            pub = (pub_el.text or "").strip() if pub_el is not None else ""
            entries.append(
                {
                    "title": _clean_html_text(title),
                    "summary": _clean_html_text(desc),
                    "link": link,
                    "published_hint": pub,
                    "feed_url": feed_url,
                }
            )
        return entries

    if tag == "feed":  # Atom
        for entry in root.findall("entry"):
            title_el = entry.find("title")
            title = (title_el.text or "").strip() if title_el is not None else ""
            link = ""
            for ln in entry.findall("link"):
                if ln.get("rel") in (None, "alternate"):
                    link = ln.get("href") or ""
                    break
            if not link:
                ln = entry.find("link")
                if ln is not None:
                    link = ln.get("href") or ""
            summary_el = entry.find("summary")
            if summary_el is None:
                summary_el = entry.find("content")
            desc = ""
            if summary_el is not None:
                desc = (summary_el.text or "").strip()
                if not desc and list(summary_el):
                    desc = "".join(summary_el.itertext()).strip()
            pub_el = entry.find("published")
            if pub_el is None:
                pub_el = entry.find("updated")
            pub = (pub_el.text or "").strip() if pub_el is not None else ""
            entries.append(
                {
                    "title": _clean_html_text(title),
                    "summary": _clean_html_text(desc),
                    "link": link,
                    "published_hint": pub,
                    "feed_url": feed_url,
                }
            )
        return entries

    return entries


_TAG_RE = re.compile(r"<[^>]+>")


def _clean_html_text(s: str) -> str:
    if not s:
        return ""
    t = _TAG_RE.sub(" ", s)
    t = re.sub(r"\s+", " ", t).strip()
    # Decode numeric entities minimally
    t = t.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return t


def entry_to_candidate(entry: dict[str, Any], retrieved_at: str | None = None) -> dict[str, Any]:
    """Build CandidateFinding dict."""
    now = retrieved_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    title = str(entry.get("title") or "")
    summary = str(entry.get("summary") or "")
    link = str(entry.get("link") or "")
    feed_url = str(entry.get("feed_url") or "")
    canonical = f"{title}\n{summary}\n{link}".encode("utf-8")
    raw_hash = hashlib.sha256(canonical).hexdigest()
    cid = f"candidate-rss-{raw_hash[:16]}"
    conf = 0.55 if len(summary) > 80 else 0.35
    return {
        "id": cid,
        "status": "candidate",
        "title": title,
        "summary": summary,
        "summary_raw": summary,
        "source_urls": [link] if link else [],
        "retrieved_at": now,
        "license_note": "Third-party feed content; cite URL only; verify license before redistribution.",
        "confidence": conf,
        "raw_hash": raw_hash,
        "feed_url": feed_url,
    }


def ingest_allowlisted_feed(
    feed_url: str,
    allowlist_path: Path,
    *,
    timeout_s: float = 30.0,
) -> list[dict[str, Any]]:
    allowed = load_allowlist(allowlist_path)
    _ensure_allowed(feed_url, allowed)
    xml_bytes = fetch_feed_xml(feed_url, timeout_s=timeout_s)
    raw_entries = parse_feed_entries(xml_bytes, feed_url)
    return [entry_to_candidate(e) for e in raw_entries]


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
