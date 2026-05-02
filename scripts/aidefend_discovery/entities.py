"""Lightweight entity extraction from free text (CVE, GHSA, CWE)."""

from __future__ import annotations

import re
from typing import Any


_CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
_GHSA = re.compile(r"\bGHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}\b", re.IGNORECASE)
_CWE = re.compile(r"\bCWE-\d{1,4}\b", re.IGNORECASE)


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


def extract_entities(text: str) -> dict[str, list[str]]:
    if not text:
        return {"cves": [], "ghsas": [], "cwes": []}
    cves = _uniq([m.group(0).upper() for m in _CVE.finditer(text)])
    ghsas = _uniq([m.group(0) for m in _GHSA.finditer(text)])
    cwes = _uniq([m.group(0).upper() for m in _CWE.finditer(text)])
    return {"cves": cves, "ghsas": ghsas, "cwes": cwes}


def merge_entity_dicts(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "cves": _uniq(a.get("cves", []) + b.get("cves", [])),
        "ghsas": _uniq(a.get("ghsas", []) + b.get("ghsas", [])),
        "cwes": _uniq(a.get("cwes", []) + b.get("cwes", [])),
    }


def entities_block(entities: dict[str, Any]) -> str:
    """Single string for BM25 / threat-style retrieval (deterministic order)."""
    parts: list[str] = []
    for k in ("cves", "ghsas", "cwes"):
        for item in entities.get(k) or []:
            parts.append(str(item))
    return " ".join(parts)
