"""Explain BM25 neighbors via lexical overlap (query tokens ∩ doc tokens, ranked by IDF)."""

from __future__ import annotations

from aidefend_discovery.bm25_index import tokenize


def top_overlap_terms(
    query: str,
    doc_text: str,
    idf: dict[str, float],
    *,
    limit: int = 12,
) -> list[str]:
    common = set(tokenize(query)) & set(tokenize(doc_text))
    if not common:
        return []
    return sorted(common, key=lambda t: idf.get(t, 0.0), reverse=True)[:limit]
