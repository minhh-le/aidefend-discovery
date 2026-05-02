# Web extraction for discovery pipelines: crawl4ai vs lighter paths

Date: 2026-05-02  
Topic: AIDEFEND discovery Phase 1+ ingestion — how to reduce HTML clutter without over-engineering.

> **Method:** Host-side discover pass (WebSearch + WebFetch + official docs). This repo has no `_infra/discoveries/` tree; synthesis lives here per project convention. For the full **Cursor `/discover` + `/codex` worker** workflow (primary-source sweeps with `crwl`), run that separately and merge conclusions into this file or append a new dated row to `INDEX.md`.

---

## Executive summary

For **feed URL → clean text → BM25/embeddings**, the best default is usually **fetch HTML once, then extract with a fast heuristic library (e.g. Trafilatura)**. Add **crawl4ai** (Playwright-class) when you **must render JavaScript**, need **deep multi-page crawl**, or want **built-in “fit markdown” / BM25 pruning / CSS schema extraction** in one stack. Crawl4AI’s own docs emphasize **LLM-free strategies** (CSS/XPath/regex) when structure is stable—aligning with cost and determinism goals for a security-intel pipeline.

---

## Stage 1 — Framed question

| Field | Content |
|--------|---------|
| Subject | Tooling choices to replace noisy RSS/HTML with retrieval-friendly text |
| Context | AIDEFEND Discovery prototype; roadmap Phase 1 (chunk, entity extract, explainability) |
| Decision supported | Whether to standardize on crawl4ai vs lighter extractors vs hybrid |
| Assumptions | Sources remain allowlisted; legal/ToS respected; no auto-promotion to AIDEFEND |

---

## Stage 3 — Comparison matrix

| Criterion | Trafilatura (or fetch + trafilatura) | crawl4ai | Paid reader APIs |
|-----------|----------------------------------------|----------|-------------------|
| Fit for feed-follower (single article URL) | Strong: static HTML path is fast, low ops | Overkill unless JS-heavy | Good fallback; cost + data policy |
| Complexity | Low (stdlib HTTP + pip dep) | Higher (browser, caching, config) | Low API, vendor lock-in |
| Operating cost | CPU + bandwidth | RAM, browser pool, longer runs | Per-request $ |
| Risk | Fails on JS-only pages | Heavier attack surface in CI; more moving parts | Terms, egress, logging |
| Best for | Blogs, advisories with HTML in response | SPAs, doc sites behind client render, adaptive crawl | Broken static fetch, urgent POC |
| Avoid when | You need rendered DOM | You only have static HTML and want minimal deps | Budget/policy forbids |

---

## Stage 4 — Gap analysis

### Gap: Noisy Atom summaries

- **Current:** Full `<content>` blobs from feeds inflate reports and dilute BM25.
- **Better approach:** Store `source_url`; fetch page; run **Trafilatura** on HTML; cap bytes; chunk for retrieval; keep raw HTML hash optional.
- **Impact:** High  
- **Effort:** Medium  
- **Source:** Practitioner pattern (DEV “skip the browser” series); Trafilatura positioning on static HTML limits.

### Gap: JS-rendered security bulletins

- **Current:** Plain `urllib` cannot see post-load content.
- **Better approach:** **crawl4ai** `AsyncWebCrawler` + `CrawlerRunConfig` with markdown / `PruningContentFilter` / `BM25ContentFilter` per official docs and tutorials (MarkTechPost walkthrough, 2026).
- **Impact:** Medium  
- **Effort:** Medium  
- **Source:** [Crawl4AI docs — strategies](https://docs.crawl4ai.com/core/markdown-generation/) (linked from crawl4ai.com); [MarkTechPost implementation piece](https://www.marktechpost.com/2026/04/14/a-coding-implementation-of-crawl4ai-for-web-crawling-markdown-generation-javascript-execution-and-llm-based-structured-extraction/) (Apr 2026).

### Gap: Structured entities (CVE, GHSA)

- **Current:** Regex only in prototype.
- **Better approach:** Prefer **RegexExtractionStrategy** / schema extraction in crawl4ai when templates stable; otherwise regex on extracted text—**before** paying for LLM extraction.
- **Impact:** High  
- **Effort:** Low–medium  
- **Source:** [LLM-free strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies) — “Why No LLM Is Often Better”; strategy selection guide.

---

## Synthesis — priorities

**Quick wins**

1. Add optional **fetch + Trafilatura** path for `source_urls` after RSS step; persist `body_extracted` + `extraction_method`.
2. Hard cap stored text (e.g. 32–64 KiB) with explicit truncation marker for audit.

**Strategic investments**

3. Introduce **crawl4ai** behind a feature flag for allowlisted domains that fail static extraction or need JS.
4. Per-domain **CSS/XPath schemas** for recurring sources (vendor advisories)—LLM-free extraction in crawl4ai.

**Nice-to-have**

5. crawl4ai **BM25ContentFilter** aligned with same query used downstream for consistency experiments.

**Work to avoid (for now)**

- Defaulting every connector to full browser crawl (cost, flake, ToS risk).
- LLM-based page extraction as the first pass (non-deterministic, expensive); reserve for edge cases after regex/CSS fails.

---

## Disregard list

- Treating **any** single extractor as “clutter-free” without per-site validation.
- Crawling **taxonomy anchor** sites when **official JSON/PDF/stix** feeds exist (per [MAINTAINER_ALIGNMENT](../MAINTAINER_ALIGNMENT.md)).
- Replacing **API-first** NVD/GitHub Advisory flows with HTML scraping.

---

## Sources (consulted / rejected)

| Source | Contribution |
|--------|----------------|
| [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) (Apache-2.0, active 2026) | Positioning: LLM-ready markdown, async crawler, extraction strategies, BM25 filters. |
| [crawl4ai.com / docs](http://crawl4ai.com/) (WebSearch snippet) | Feature list: Fit Markdown, adaptive crawl, chunking. |
| [LLM-free strategies](https://docs.crawl4ai.com/extraction/no-llm-strategies) | Regex/CSS/XPath first; when LLM extraction is justified. |
| [Strategies API](http://crawl4ai.com/api/strategies/) | Strategy selection guide (regex vs CSS vs LLM vs cosine). |
| [MarkTechPost — Crawl4AI v0.8.x tutorial](https://www.marktechpost.com/2026/04/14/a-coding-implementation-of-crawl4ai-for-web-crawling-markdown-generation-javascript-execution-and-llm-based-structured-extraction/) (Apr 2026) | Practical: `PruningContentFilter`, `BM25ContentFilter`, CSS extraction patterns. |
| [Contextractor / Trafilatura overview](https://www.contextractor.com/trafilatura/) | Heuristic extractors strong on static HTML; SIGIR/benchmark narrative; JS limitation. |
| [ScrapingHub article-extraction-benchmark](https://github.com/scrapinghub/article-extraction-benchmark) | Independent F1 table context (trafilatura vs readability family). |
| [DEV — Browser tools Part 4](https://dev.to/stevengonsalvez/browser-tools-for-ai-agents-part-4-skip-the-browser-save-80-on-tokens-304c) | Decision tree: static → extractor first; JS → render then extract. |
| **Rejected as primary:** Jina Reader / Firecrawl-style hosted readers | Skill + alignment: recovery paths, not default; policy/cost sensitive. |

---

## Contradictions / humility

- Benchmarks vary by **domain** (news vs docs vs product pages). SIGIR/contextractor claims are directional; re-validate on **your** allowlisted hosts.
- Crawl4AI marketing stresses speed and “#1 trending”; engineering judgment should come from **pilot metrics** on target URLs, not star count.
