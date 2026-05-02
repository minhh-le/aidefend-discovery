#!/usr/bin/env python3
"""
Thin vertical slice: RSS (allowlisted) → CandidateFinding JSONL → BM25 vs AIDEFEND baseline → GapReport JSON.

Example:
  python3 scripts/run_discovery_gap.py \\
    --data-json ../aidefense-framework/data/data.json \\
    --feed-url https://github.com/langchain-ai/langchain/releases.atom \\
    --allowlist lab/aidefend_discovery/feeds.allowlist \\
    --max-items 15 \\
    --top-k 5
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from aidefend_discovery.baseline import (  # noqa: E402
    TechniqueRecord,
    extract_threat_ids,
    flatten_techniques,
    load_data_json,
)
from aidefend_discovery.bm25_index import BM25Index  # noqa: E402
from aidefend_discovery.explain import top_overlap_terms  # noqa: E402
from aidefend_discovery.extract import (  # noqa: E402
    enrich_candidate,
    load_host_allowlist,
)
from aidefend_discovery.rss_ingest import (  # noqa: E402
    append_jsonl,
    ingest_allowlisted_feed,
)


def _threat_overlap(candidate_text: str, records: list[TechniqueRecord]) -> tuple[list[str], list[str]]:
    """Return (candidate_ids_found, technique_ids_with_item_overlap)."""
    cand_ids = extract_threat_ids(candidate_text)
    if not cand_ids:
        return [], []
    lowered = candidate_text.lower()
    matched_tech: set[str] = set()
    for r in records:
        blob = " ".join(r.threat_items).lower()
        for cid in cand_ids:
            if cid.lower() in blob or cid.lower() in lowered:
                # Confirm item substring overlap with threat corpus
                if cid.lower() in blob:
                    matched_tech.add(r.id)
                    break
    return cand_ids, sorted(matched_tech)


def build_gap_report(
    candidate: dict,
    records: list[TechniqueRecord],
    index: BM25Index,
    *,
    top_k: int,
    gap_bm25_max: float,
) -> dict:
    queries = candidate.get("retrieval_chunk_queries") or []
    if not queries:
        queries = [f"{candidate.get('title', '')}\n{candidate.get('summary', '')}"]
    ranked = index.top_k_pooled(queries, top_k)
    query_for_overlap = "\n".join(queries[:5])[:14000]
    idf = index.idf_vector()
    ids_scores: list[tuple[str, float]] = []
    overlap_terms_nested: list[list[str]] = []
    for idx, score in ranked:
        if 0 <= idx < len(records):
            r = records[idx]
            ids_scores.append((r.id, score))
            overlap_terms_nested.append(
                top_overlap_terms(query_for_overlap, r.search_text(), idf, limit=12)
            )
    nearest_ids = [i for i, _ in ids_scores]
    scores_only = [s for _, s in ids_scores]
    max_bm25 = max(scores_only) if scores_only else 0.0
    cand_ids, tech_overlap = _threat_overlap(query_for_overlap, records)

    weak_lexical = max_bm25 < gap_bm25_max
    orphan_ids = bool(cand_ids) and not tech_overlap
    is_gap = weak_lexical or orphan_ids
    reasons: list[str] = []
    if weak_lexical:
        reasons.append(f"max_bm25_below_threshold({max_bm25:.4f}<{gap_bm25_max})")
    if orphan_ids:
        reasons.append("threat_ids_in_text_but_no_framework_line_overlap")

    sugg_tactics: set[str] = set()
    sugg_pillars: set[str] = set()
    sugg_phases: set[str] = set()
    for idx, _ in ranked[:3]:
        if 0 <= idx < len(records):
            r = records[idx]
            sugg_tactics.add(r.tactic_id)
            sugg_pillars.update(r.pillars)
            sugg_phases.update(r.phases)

    return {
        "candidate_id": candidate["id"],
        "nearest_technique_ids": nearest_ids,
        "bm25_scores": scores_only,
        "max_bm25": max_bm25,
        "threat_id_overlap": tech_overlap,
        "candidate_threat_tokens": cand_ids,
        "nearest_lexical_overlap_terms": overlap_terms_nested,
        "is_gap": is_gap,
        "gap_reason": "; ".join(reasons) if reasons else "not_gap",
        "suggested_tactic_ids": sorted(sugg_tactics),
        "suggested_pillars": sorted(sugg_pillars),
        "suggested_phases": sorted(sugg_phases),
        "rationale": "BM25 top-k (max-pooled over chunk queries) vs AIDEFEND techniques; threat IDs vs defendsAgainst; lexical overlap terms for review.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AIDEFEND discovery gap prototype slice")
    parser.add_argument(
        "--data-json",
        type=Path,
        required=True,
        help="Path to aidefense-framework data/data.json",
    )
    parser.add_argument("--feed-url", required=True, help="RSS or Atom URL (must be in allowlist)")
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=ROOT / "lab" / "aidefend_discovery" / "feeds.allowlist",
        help="Path to newline-separated allowed feed URLs",
    )
    parser.add_argument(
        "--candidates-out",
        type=Path,
        default=ROOT / "lab" / "aidefend_discovery" / "candidates.jsonl",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--gap-bm25-max",
        type=float,
        default=8.0,
        help="Mark is_gap when max BM25 score is below this (tune per corpus / feed).",
    )
    parser.add_argument("--max-items", type=int, default=25, help="Cap feed items processed")
    parser.add_argument("--dry-run", action="store_true", help="Do not append candidates JSONL")
    parser.add_argument(
        "--fetch-pages",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch source_urls HTML and extract main text with Trafilatura (hosts must be in page fetch allowlist).",
    )
    parser.add_argument(
        "--page-fetch-allowlist",
        type=Path,
        default=ROOT / "lab" / "aidefend_discovery" / "page_fetch.allowlist",
        help="Hostnames permitted for page fetch (one per line).",
    )
    parser.add_argument("--body-max-kb", type=int, default=48, help="Max UTF-8 bytes for stored extracted body")
    parser.add_argument("--chunk-size", type=int, default=3500, help="Retrieval chunk size (chars)")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap (chars)")
    parser.add_argument("--fetch-timeout", type=float, default=25.0, help="HTTP timeout for page fetch")
    args = parser.parse_args()

    data = load_data_json(args.data_json)
    records = flatten_techniques(data)
    if not records:
        print("ERROR: no techniques loaded from data.json", file=sys.stderr)
        return 1

    corpus = [r.search_text() for r in records]
    index = BM25Index(corpus)

    candidates = ingest_allowlisted_feed(args.feed_url, args.allowlist)
    candidates = candidates[: max(0, args.max_items)]

    hosts = load_host_allowlist(args.page_fetch_allowlist)
    body_max = max(1024, args.body_max_kb * 1024)

    for c in candidates:
        enrich_candidate(
            c,
            fetch_pages=args.fetch_pages,
            host_allowlist=hosts,
            body_max_bytes=body_max,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            fetch_timeout_s=args.fetch_timeout,
        )

    reports: list[dict] = []
    for c in candidates:
        reports.append(
            build_gap_report(
                c,
                records,
                index,
                top_k=args.top_k,
                gap_bm25_max=args.gap_bm25_max,
            )
        )

    if not args.dry_run:
        append_jsonl(args.candidates_out, candidates)

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_path = args.reports_dir / f"gap_run_{stamp}.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_json": str(args.data_json.resolve()),
        "feed_url": args.feed_url,
        "technique_records": len(records),
        "candidates": candidates,
        "gap_reports": reports,
        "params": {
            "top_k": args.top_k,
            "gap_bm25_max": args.gap_bm25_max,
            "max_items": args.max_items,
            "phase1": {
                "fetch_pages": args.fetch_pages,
                "page_fetch_allowlist": str(args.page_fetch_allowlist),
                "body_max_bytes": body_max,
                "chunk_size": args.chunk_size,
                "chunk_overlap": args.chunk_overlap,
                "extraction": "trafilatura",
            },
        },
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {report_path}")
    if not args.dry_run:
        print(f"Appended {len(candidates)} candidates to {args.candidates_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
