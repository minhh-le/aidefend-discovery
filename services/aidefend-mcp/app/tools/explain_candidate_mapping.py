"""
explain_candidate_mapping — full reasoning trace for a discovery candidate.

Returns the candidate's full GapReport: BM25 nearest techniques, lexical
overlap terms (IDF-ranked), bridge rationales (from CWE→tactic table),
suggested pillar/phase, and provenance (source_urls, content_hash,
retrieved_at).

All AID-* IDs are confined to the `references_aid` sidecar so the wall
between hypothesis and official defense holds.
"""

from __future__ import annotations

from typing import Any

from app.discovery import (
    discovery_namespace_response,
    is_discovery_configured,
)
from app.discovery.store import get_candidate_detail
from app.logger import get_logger

logger = get_logger(__name__)


async def explain_candidate_mapping(candidate_id: str) -> dict[str, Any]:
    """Return the full reasoning trace for one candidate.

    Args:
        candidate_id: e.g., "candidate-rss-fc6b6f475cd72909" or
                     "candidate-nvd-..." or "candidate-ghsa-...".

    Returns dict with:
        discovery_namespace, configured, disclaimer (always)
        candidate (when found): summary, entities, source_urls,
            retrieval_chunks, body_extracted (if any), and:
        gap_report: BM25 nearest_technique_ids, scores,
            nearest_lexical_overlap_terms, bridge_rationales,
            threat_id_overlap, gap_reason, etc.
        references_aid (sidecar) + references_aid_note (disclaimer)
    """
    logger.info("explain_candidate_mapping: candidate_id=%r", candidate_id)

    if not is_discovery_configured():
        return discovery_namespace_response(
            configured=False,
            error="DISCOVERY_DB_PATH is not set; discovery layer is unavailable.",
        )

    if not candidate_id or not isinstance(candidate_id, str):
        return discovery_namespace_response(
            configured=True,
            error="candidate_id is required and must be a non-empty string.",
        )

    try:
        detail = get_candidate_detail(candidate_id.strip())
    except Exception as e:
        logger.exception("explain_candidate_mapping failed")
        return discovery_namespace_response(
            configured=True,
            error=f"discovery detail query failed: {type(e).__name__}: {e}",
        )

    if detail is None:
        return discovery_namespace_response(
            configured=True,
            error=f"candidate not found: {candidate_id}",
        )

    if not detail.get("source_urls"):
        # Contract: explain must always cite at least one source. If the store
        # row has none (shouldn't happen with the current ingest), surface it.
        logger.warning("candidate %s has no source_urls; ingest invariant broken", candidate_id)

    return discovery_namespace_response(
        configured=True,
        payload={"candidate": detail},
    )
