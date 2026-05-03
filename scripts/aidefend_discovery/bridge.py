"""CWE → AIDEFEND tactic/pillar/phase bridge.

Loads a YAML table mapping CWE IDs to suggested tactic hints with rationales
and citations, then produces hint-merge output for GapReport given a candidate's
extracted entities.

Design:
- Bridge table is YAML so non-engineers can extend it via PR.
- Each entry carries `confidence` (0..1) and `source` (citation URL) so the
  rationale string in the GapReport is auditable.
- Suggestions are *additive hints* — they augment BM25-derived suggestions,
  never replace them. Reviewer always has final say.
- Loader caches by file mtime; cheap to call per-run.

The output is a small structured dict (not a dataclass) to keep the GapReport
JSON serialization trivial.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError as exc:  # pragma: no cover
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc

LOG = logging.getLogger(__name__)


_BridgeEntry = dict[str, Any]
_Cache: dict[str, tuple[float, list[_BridgeEntry]]] = {}


def load_bridge(path: Path) -> list[_BridgeEntry]:
    """Read and validate the YAML bridge table; cached by mtime."""
    if yaml is None:
        raise RuntimeError("pyyaml is required for bridge support; pip install pyyaml")
    p = Path(path)
    key = str(p.resolve())
    mtime = p.stat().st_mtime
    cached = _Cache.get(key)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_bridges = data.get("bridges") or []
    if not isinstance(raw_bridges, list):
        raise ValueError(f"bridge table at {path} must have a list under 'bridges'")

    out: list[_BridgeEntry] = []
    for i, entry in enumerate(raw_bridges):
        if not isinstance(entry, dict):
            raise ValueError(f"bridge entry {i} must be a mapping")
        cwe_id = str(entry.get("cwe_id", "")).strip().upper()
        if not cwe_id.startswith("CWE-"):
            raise ValueError(f"bridge entry {i}: cwe_id missing or malformed: {cwe_id!r}")
        out.append(
            {
                "cwe_id": cwe_id,
                "pillar": list(entry.get("pillar") or []),
                "phase": list(entry.get("phase") or []),
                "suggested_tactic_ids": list(entry.get("suggested_tactic_ids") or []),
                "rationale": str(entry.get("rationale") or "").strip(),
                "confidence": float(entry.get("confidence") or 0.0),
                "source": str(entry.get("source") or "").strip(),
            }
        )
    _Cache[key] = (mtime, out)
    return out


def suggest_from_entities(
    entities: dict[str, list[str]] | None,
    bridges: list[_BridgeEntry],
) -> dict[str, list[str]]:
    """Given a candidate's `entities`, return additive hints for the GapReport.

    Returns a dict shaped like:
      {
        "pillars": [...],
        "phases": [...],
        "suggested_tactic_ids": [...],
        "rationales": ["CWE-94: <rationale> (conf 0.85; src <url>)", ...],
      }

    Order of rationales follows CWE order in the entity list. Bridges with
    confidence 0.0 are skipped.
    """
    out_pillars: list[str] = []
    out_phases: list[str] = []
    out_tactics: list[str] = []
    out_rationales: list[str] = []
    if not entities:
        return {"pillars": [], "phases": [], "suggested_tactic_ids": [], "rationales": []}

    by_cwe = {b["cwe_id"]: b for b in bridges}
    seen_pillars: set[str] = set()
    seen_phases: set[str] = set()
    seen_tactics: set[str] = set()

    for cwe_id in entities.get("cwes") or []:
        norm = str(cwe_id).strip().upper()
        b = by_cwe.get(norm)
        if not b or b["confidence"] <= 0:
            continue
        for p in b["pillar"]:
            if p not in seen_pillars:
                seen_pillars.add(p)
                out_pillars.append(p)
        for ph in b["phase"]:
            if ph not in seen_phases:
                seen_phases.add(ph)
                out_phases.append(ph)
        for t in b["suggested_tactic_ids"]:
            if t not in seen_tactics:
                seen_tactics.add(t)
                out_tactics.append(t)
        out_rationales.append(
            f"{norm}: {b['rationale']} (conf {b['confidence']:.2f}; src {b['source']})"
        )

    return {
        "pillars": out_pillars,
        "phases": out_phases,
        "suggested_tactic_ids": out_tactics,
        "rationales": out_rationales,
    }


def default_bridge_path() -> Path:
    """Default location of the bridge table relative to repo root."""
    return (
        Path(__file__).resolve().parents[2]
        / "lab"
        / "aidefend_discovery"
        / "bridges"
        / "cwe_to_tactic.yaml"
    )


def load_default_bridge_or_empty() -> list[_BridgeEntry]:
    """Best-effort default: return the bundled bridge or [] if pyyaml/file missing."""
    try:
        path = default_bridge_path()
        if not path.exists():
            return []
        return load_bridge(path)
    except Exception as e:  # pragma: no cover - defensive
        LOG.warning("bridge load failed: %s", e)
        return []
