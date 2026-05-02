"""Load AIDEFEND ``data.json`` and flatten techniques for lexical retrieval."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


_WS_RE = re.compile(r"\s+")


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    # Unescape entities, drop tags crudely (dataset uses minimal HTML)
    t = html.unescape(text)
    t = re.sub(r"<[^>]+>", " ", t)
    return _WS_RE.sub(" ", t).strip()


_THREAT_ID_PATTERN = re.compile(
    r"\b(?:AML\.[T]\d+(?:\.\d+)?|LLM\d+(?::\d+)?|ML\d+(?::\d+)?|ASI\d+(?::\d+)?|"
    r"MAES[\-\.]?\d+|NISTAML\.\d+|NIST\.?\s*AML\.?\d+|ATLAS\.|ATT&CK|[\w]+\.T\d+)\b",
    re.IGNORECASE,
)


def extract_threat_ids(text: str) -> list[str]:
    """Heuristic threat/framework id tokens for overlap checks."""
    found = _THREAT_ID_PATTERN.findall(text or "")
    # Normalize trivial variants
    out: list[str] = []
    seen: set[str] = set()
    for raw in found:
        key = raw.strip().upper().replace("ATT&CK", "ATTACK")
        if key not in seen:
            seen.add(key)
            out.append(raw.strip())
    return out


@dataclass(frozen=True)
class TechniqueRecord:
    """Single searchable unit (technique or sub-technique)."""

    id: str
    name: str
    tactic_id: str
    tactic_name: str
    parent_id: str | None
    description: str
    keywords: tuple[str, ...]
    threat_items: tuple[str, ...]  # "Framework :: item"
    pillars: tuple[str, ...]
    phases: tuple[str, ...]

    def search_text(self) -> str:
        parts = [
            self.id,
            self.name,
            self.tactic_name,
            self.description,
            " ".join(self.keywords),
            " ".join(self.threat_items),
            " ".join(self.pillars),
            " ".join(self.phases),
        ]
        return _WS_RE.sub(" ", " ".join(p for p in parts if p)).strip()


def _iter_defends_against(defends: Any) -> Iterator[str]:
    if not isinstance(defends, list):
        return
    for block in defends:
        if not isinstance(block, dict):
            continue
        fw = str(block.get("framework") or "").strip()
        items = block.get("items") or []
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, str):
                continue
            s = it.strip()
            if not s or s.startswith("N/A"):
                continue
            yield f"{fw} :: {s}" if fw else s


def _flatten_technique(
    tactic_id: str,
    tactic_name: str,
    node: dict[str, Any],
    parent_id: str | None,
) -> Iterator[TechniqueRecord]:
    tid = str(node.get("id") or "")
    name = strip_html(str(node.get("name") or ""))
    desc = strip_html(str(node.get("description") or ""))
    kw_raw = node.get("keywords") or []
    keywords = tuple(
        strip_html(str(k)).lower()
        for k in kw_raw
        if isinstance(k, str) and strip_html(k)
    )
    pillars_raw = node.get("pillar") or []
    pillars = tuple(str(p) for p in pillars_raw if isinstance(p, str))
    phases_raw = node.get("phase") or []
    phases = tuple(str(p) for p in phases_raw if isinstance(p, str))
    threat_items = tuple(sorted(set(_iter_defends_against(node.get("defendsAgainst")))))

    if tid:
        yield TechniqueRecord(
            id=tid,
            name=name,
            tactic_id=tactic_id,
            tactic_name=tactic_name,
            parent_id=parent_id,
            description=desc,
            keywords=keywords,
            threat_items=threat_items,
            pillars=pillars,
            phases=phases,
        )

    subs = node.get("subTechniques") or []
    if isinstance(subs, list):
        for sub in subs:
            if isinstance(sub, dict):
                yield from _flatten_technique(tactic_id, tactic_name, sub, tid or parent_id)


def load_data_json(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def flatten_techniques(data: dict[str, Any]) -> list[TechniqueRecord]:
    """Flatten all tactics → techniques → subTechniques from bundled ``data.json``."""
    out: list[TechniqueRecord] = []
    tactics = data.get("tactics") or []
    if not isinstance(tactics, list):
        return out
    for tac in tactics:
        if not isinstance(tac, dict):
            continue
        tactic_id = str(tac.get("id") or "")
        tactic_name = strip_html(str(tac.get("name") or tactic_id))
        techniques = tac.get("techniques") or []
        if not isinstance(techniques, list):
            continue
        for tech in techniques:
            if isinstance(tech, dict):
                out.extend(_flatten_technique(tactic_id, tactic_name, tech, None))
    return out


def records_by_id(records: list[TechniqueRecord]) -> dict[str, TechniqueRecord]:
    return {r.id: r for r in records if r.id}
