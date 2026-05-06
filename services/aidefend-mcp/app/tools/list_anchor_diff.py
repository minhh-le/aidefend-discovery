"""
list_anchor_diff — surface taxonomy-anchor regressions from the latest run.

Reads the most recent `reports/anchor_diff_*.json` produced by the
aidefend-discovery `anchor_diff.py` script. Returns per-framework
missing-from-AIDEFEND lists so reviewers can see at a glance which upstream
taxonomy IDs lack curated mappings.

This is the architectural answer to taxonomy drift; pair with the
upstream Promotion Playbook before opening a Shape-B promotion PR.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.discovery import (
    DISCOVERY_DISCLAIMER,
    discovery_namespace_response,
    is_discovery_configured,
)
from app.discovery.store import latest_anchor_diff_path
from app.logger import get_logger

logger = get_logger(__name__)


async def list_anchor_diff(framework: Optional[str] = None) -> dict[str, Any]:
    """Return missing-from-AIDEFEND anchor IDs from the latest diff report.

    Args:
        framework: optional substring filter (e.g., 'OWASP', 'NIST') —
                   case-insensitive substring match against the framework
                   name. None returns every framework.

    Returns dict with:
        discovery_namespace, configured, disclaimer (always)
        report_path: filesystem path of the report consulted
        generated_at: timestamp of the report
        diffs[]: per-framework {framework, version, snapshot_date,
                 source_url, missing_from_aidefend[],
                 present_in_aidefend[], coverage_ratio}
    """
    logger.info("list_anchor_diff: framework=%r", framework)

    if not is_discovery_configured():
        return discovery_namespace_response(
            configured=False,
            error="DISCOVERY_DB_PATH is not set; discovery layer is unavailable.",
        )

    path = latest_anchor_diff_path()
    if path is None:
        return discovery_namespace_response(
            configured=True,
            error=(
                "no anchor_diff_*.json found under DISCOVERY_REPORTS_PATH; "
                "run `python3 scripts/anchor_diff.py --data-json ...` in the "
                "aidefend-discovery repo to generate one."
            ),
        )

    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        logger.exception("list_anchor_diff: parse failed")
        return discovery_namespace_response(
            configured=True,
            error=f"failed to read {path.name}: {type(e).__name__}: {e}",
        )

    diffs = payload.get("diffs") or []
    if framework:
        needle = framework.lower()
        diffs = [d for d in diffs if needle in str(d.get("framework", "")).lower()]

    # Note explicitly: anchor_diff items are upstream framework IDs (MITRE
    # ATLAS / OWASP / NIST / etc.). They are NOT AID-* IDs — the wall holds.
    return discovery_namespace_response(
        configured=True,
        payload={
            "report_path": str(path),
            "generated_at": payload.get("generated_at"),
            "data_json": payload.get("data_json"),
            "framework_count": len(diffs),
            "diffs": diffs,
            "ids_note": (
                "missing_from_aidefend[] entries are upstream framework IDs "
                "(MITRE ATLAS, OWASP, NIST, MAESTRO, SAIF, DASF, AITech) — "
                "not AIDEFEND AID-* IDs. " + DISCOVERY_DISCLAIMER
            ),
        },
    )
