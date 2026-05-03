#!/usr/bin/env python3
"""HEAD-check every URL in the feeds allowlist; emit a dated audit report.

Exit codes:
  0 — at least one feed is reachable.
  1 — all feeds dead or allowlist empty.

Output: reports/feed_audit_YYYYMMDD.json with per-feed status, latency, last-modified.

Usage:
  python3 scripts/audit_feeds.py \
    --allowlist lab/aidefend_discovery/feeds.allowlist \
    [--output reports/feed_audit_$(date -u +%Y%m%d).json] \
    [--timeout 10] [--user-agent ...]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_USER_AGENT = (
    "aidefend-discovery-feed-audit/0.1 "
    "(+https://github.com/minhh-le/persistent-agent-security; research prototype)"
)


def load_allowlist(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def head_check(url: str, timeout_s: float, user_agent: str) -> dict[str, object]:
    """HEAD with a GET fallback (some servers don't support HEAD)."""
    started = time.monotonic()
    base = {
        "url": url,
        "reachable": False,
        "status": None,
        "method": None,
        "last_modified": None,
        "etag": None,
        "content_type": None,
        "latency_ms": None,
        "error": None,
    }
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers={"User-Agent": user_agent})
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                # Read at most 1 KiB on GET to keep the audit cheap.
                if method == "GET":
                    resp.read(1024)
                base.update(
                    {
                        "reachable": True,
                        "status": resp.status,
                        "method": method,
                        "last_modified": resp.headers.get("Last-Modified"),
                        "etag": resp.headers.get("ETag"),
                        "content_type": resp.headers.get("Content-Type"),
                        "latency_ms": int((time.monotonic() - started) * 1000),
                    }
                )
                return base
        except urllib.error.HTTPError as e:
            base["status"] = e.code
            base["method"] = method
            base["error"] = f"HTTPError {e.code}"
            if method == "HEAD" and e.code in (400, 405, 501):
                continue  # try GET as fallback
            base["latency_ms"] = int((time.monotonic() - started) * 1000)
            return base
        except urllib.error.URLError as e:
            base["error"] = f"URLError {e.reason!r}"
            base["latency_ms"] = int((time.monotonic() - started) * 1000)
            return base
        except Exception as e:  # pragma: no cover — defensive
            base["error"] = f"{type(e).__name__}: {e}"
            base["latency_ms"] = int((time.monotonic() - started) * 1000)
            return base
    base["latency_ms"] = int((time.monotonic() - started) * 1000)
    return base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "lab" / "aidefend_discovery" / "feeds.allowlist",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args(argv)

    feeds = load_allowlist(args.allowlist)
    if not feeds:
        print(f"ERROR: allowlist {args.allowlist} is empty", file=sys.stderr)
        return 1

    print(f"INFO: auditing {len(feeds)} feed(s) from {args.allowlist}", file=sys.stderr)
    results = [head_check(u, args.timeout, args.user_agent) for u in feeds]
    reachable = sum(1 for r in results if r["reachable"])

    out_path = args.output or (
        Path(__file__).resolve().parents[1]
        / "reports"
        / f"feed_audit_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "allowlist_path": str(args.allowlist),
        "feed_count": len(feeds),
        "reachable_count": reachable,
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"INFO: {reachable}/{len(feeds)} reachable; wrote {out_path}", file=sys.stderr)

    return 0 if reachable >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
