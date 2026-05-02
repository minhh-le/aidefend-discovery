"""JSON shapes for candidates, gap reports, and review workflow."""

from __future__ import annotations

from typing import Literal, TypedDict


class CandidateFinding(TypedDict, total=False):
    """Emitted by ingestion; append-only until review changes status."""

    id: str
    status: Literal["candidate", "rejected", "promoted"]
    title: str
    summary: str
    summary_raw: str
    body_extracted: str | None
    body_truncated: bool
    body_extracted_bytes: int
    body_fetch_error: str | None
    body_fetch_skipped_reason: str | None
    body_retrieval: str
    body_retrieval_truncated: bool
    retrieval_chunks: list[dict[str, object]]
    retrieval_chunk_queries: list[str]
    entities: dict[str, list[str]]
    content_hash: str
    source_urls: list[str]
    retrieved_at: str  # ISO 8601
    license_note: str
    confidence: float  # 0..1 producer-side heuristic
    raw_hash: str  # sha256 of canonical raw bytes or normalized text
    feed_url: str
    source_type: str
    source_id: str
    kev_flag: bool


class GapReport(TypedDict, total=False):
    """One row per candidate after retrieval vs AIDEFEND baseline."""

    candidate_id: str
    nearest_technique_ids: list[str]
    bm25_scores: list[float]
    max_bm25: float
    threat_id_overlap: list[str]
    candidate_threat_tokens: list[str]
    is_gap: bool
    gap_reason: str
    suggested_tactic_ids: list[str]
    suggested_pillars: list[str]
    suggested_phases: list[str]
    rationale: str
    nearest_lexical_overlap_terms: list[list[str]]


# Review contract enums (see docs/aidefend_discovery/REVIEW_CONTRACT.md)
REJECTION_REASONS = frozenset(
    {
        "duplicate",
        "low_quality",
        "license",
        "out_of_scope",
        "already_covered",
        "false_positive",
        "needs_corroboration",
        "other",
    }
)
