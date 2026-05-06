"""
search_discovery_candidates — query the aidefend-discovery candidate store.

This is a discovery-namespace tool. Responses are *hypotheses* about what
might belong in the AIDEFEND knowledge base, not official defenses. Every
response carries `discovery_namespace: true` and the standard disclaimer.

If DISCOVERY_DB_PATH is unset, returns a graceful "not configured" payload.
"""

from __future__ import annotations

from typing import Any, Optional

from app.discovery import (
    discovery_namespace_response,
    is_discovery_configured,
)
from app.discovery.store import list_candidates
from app.logger import get_logger

logger = get_logger(__name__)


async def search_discovery_candidates(
    keyword: Optional[str] = None,
    source_type: Optional[str] = None,
    is_gap: Optional[bool] = None,
    status: Optional[str] = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """Search the discovery candidate store for hypotheses matching filters.

    Filters (all optional):
      keyword: substring match against candidate id and payload (title/summary).
      source_type: 'rss', 'nvd_api', 'ghsa_api'.
      is_gap: True returns only candidates flagged as gaps; False returns only
              non-gap candidates; None returns both.
      status: 'candidate' (pending review), 'rejected', 'promoted'.
      top_k: max results, capped at 50 internally.

    Returns a dict with:
      discovery_namespace, configured, disclaimer (always)
      results[]: per-candidate summary with title, summary, entities,
                 max_bm25, is_gap, gap_reason, bridge_rationales,
                 references_aid (sidecar — never in primary fields).
    """
    logger.info(
        "search_discovery_candidates: keyword=%r source_type=%r is_gap=%r status=%r top_k=%r",
        keyword, source_type, is_gap, status, top_k,
    )

    if not is_discovery_configured():
        return discovery_namespace_response(
            configured=False,
            error="DISCOVERY_DB_PATH is not set; discovery layer is unavailable.",
        )

    top_k = max(1, min(50, int(top_k)))
    try:
        results = list_candidates(
            keyword=keyword,
            source_type=source_type,
            is_gap=is_gap,
            status=status,
            top_k=top_k,
        )
    except Exception as e:
        logger.exception("search_discovery_candidates failed")
        return discovery_namespace_response(
            configured=True,
            error=f"discovery query failed: {type(e).__name__}: {e}",
        )

    return discovery_namespace_response(
        configured=True,
        payload={
            "filters": {
                "keyword": keyword,
                "source_type": source_type,
                "is_gap": is_gap,
                "status": status,
                "top_k": top_k,
            },
            "result_count": len(results),
            "results": results,
        },
    )
