"""Lightweight entity extraction from free text (CVE, GHSA, CWE)."""

from __future__ import annotations

import re
from typing import Any


_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
_GHSA = re.compile(r"\bGHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}\b", re.IGNORECASE)
_CWE = re.compile(r"\bCWE-\d{1,4}\b", re.IGNORECASE)

# Version-range patterns commonly seen in advisory prose / GHSA / NVD CPE strings.
# Captures: comparator-style (< 2.0.1, <= 2.0, >= 1.4, > 1.0, = 2.0), interval (1.0.0 - 2.0.1),
# and "affected: 1.0.0" / "fixed in 2.0.2". Versions are dotted numerics with optional
# pre-release tag (e.g., 1.0.0-rc1) and trailing alpha tokens limited to keep the regex tight.
_VERSION_TOKEN = r"\d+(?:\.\d+){0,3}(?:[\-+][0-9A-Za-z.]+)?"
_VERSION_COMPARATOR = re.compile(
    rf"(?<![\w.])(?P<op><=|>=|<|>|==|=)\s*(?P<ver>{_VERSION_TOKEN})\b",
)
_VERSION_INTERVAL = re.compile(
    rf"\b(?P<lo>{_VERSION_TOKEN})\s*(?:-|to|through|–)\s*(?P<hi>{_VERSION_TOKEN})\b",
)
_AFFECTED_FIXED = re.compile(
    rf"\b(?P<kind>affected|fixed\s+in|patched\s+in|introduced\s+in)\s*[:=]?\s*(?P<ver>{_VERSION_TOKEN})\b",
    re.IGNORECASE,
)


def _norm_key(s: str) -> str:
    u = s.upper()
    if u.startswith("GHSA-"):
        return s.lower()
    return u


def _uniq(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for s in seq:
        k = _norm_key(s)
        if k in seen:
            continue
        seen.add(k)
        u = s.upper()
        if u.startswith("GHSA-"):
            out.append(s.lower())
        elif u.startswith("CVE-") or u.startswith("CWE-"):
            out.append(u)
        else:
            out.append(s)
    return out


def _extract_version_constraints(text: str) -> list[str]:
    """Pull comparator, interval, and affected/fixed phrases. Order: comparator first,
    interval second, kind-prefixed third — preserves source ordering within each class."""
    out: list[str] = []
    for m in _VERSION_COMPARATOR.finditer(text):
        op = m.group("op")
        if op == "=":
            op = "=="
        out.append(f"{op} {m.group('ver')}")
    for m in _VERSION_INTERVAL.finditer(text):
        out.append(f"{m.group('lo')} - {m.group('hi')}")
    for m in _AFFECTED_FIXED.finditer(text):
        kind = re.sub(r"\s+", "_", m.group("kind").lower())
        out.append(f"{kind}:{m.group('ver')}")
    # de-dup while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for s in out:
        if s in seen:
            continue
        seen.add(s)
        result.append(s)
    return result


def extract_entities(text: str) -> dict[str, list[str]]:
    if not text:
        return {"cves": [], "ghsas": [], "cwes": [], "version_constraints": []}
    cves = _uniq([m.group(0).upper() for m in _CVE.finditer(text)])
    ghsas = _uniq([m.group(0) for m in _GHSA.finditer(text)])
    cwes = _uniq([m.group(0).upper() for m in _CWE.finditer(text)])
    version_constraints = _extract_version_constraints(text)
    return {
        "cves": cves,
        "ghsas": ghsas,
        "cwes": cwes,
        "version_constraints": version_constraints,
    }


def merge_entity_dicts(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict[str, list[str]]:
    merged_versions: list[str] = []
    seen_versions: set[str] = set()
    for v in (a.get("version_constraints") or []) + (b.get("version_constraints") or []):
        if v in seen_versions:
            continue
        seen_versions.add(v)
        merged_versions.append(v)
    return {
        "cves": _uniq(a.get("cves", []) + b.get("cves", [])),
        "ghsas": _uniq(a.get("ghsas", []) + b.get("ghsas", [])),
        "cwes": _uniq(a.get("cwes", []) + b.get("cwes", [])),
        "version_constraints": merged_versions,
    }


def entities_block(entities: dict[str, Any]) -> str:
    """Single string for BM25 / threat-style retrieval (deterministic order)."""
    parts: list[str] = []
    for k in ("cves", "ghsas", "cwes", "version_constraints"):
        for item in entities.get(k) or []:
            parts.append(str(item))
    return " ".join(parts)
