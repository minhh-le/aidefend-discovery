# AIDEFEND structured + discovery — roadmap (0 → end product)

Updated: 2026-05-03 (Phases 1, 2A, 2B, 3, 4, 5 scaffolded end-to-end; embeddings re-open trigger fired on gold eval; remaining work is precision tuning + operationalisation + first upstream promotion PR)

This document is the **persistent** plan for evolving from the current prototype in [`lab/aidefend_discovery/`](../../lab/aidefend_discovery/README.md) toward a governable **discovery layer** on top of the open AIDEFEND knowledge base. Companion docs: [`REVIEW_CONTRACT.md`](REVIEW_CONTRACT.md), [`MAINTAINER_ALIGNMENT.md`](MAINTAINER_ALIGNMENT.md).

### Related research (discover)

- [`discoveries/INDEX.md`](discoveries/INDEX.md) — dated synthesis notes.
- [2026-05-02 — Web extraction pipeline](discoveries/2026-05-02-web-extraction-pipeline.md) — crawl4ai vs Trafilatura-first vs hybrid; sources and disregard list.
- [2026-05-02 — NVD + GitHub global advisory APIs](discoveries/2026-05-02-nvd-ghsa-connector-api.md) — connector enumeration (CVE 2.0, rate limits, GHSA list/detail, auth).

**Ongoing best-practice loop:** Run a full **Cursor `/discover`** pass (with **`/codex`** workers per skill contract) when you need wide primary-source coverage; merge outcomes here as new dated entries. This host session used WebSearch/WebFetch only—sufficient for the extraction stack decision, not a substitute for deep vendor/MITRE primary reads.

---

## North star

**Structured layer:** The CC BY knowledge base (authoritative tactic modules → generated `data/data.json`), mappings, site, and MCP/REST service are bundled in this monorepo as tracked snapshots and remain the **source of approved truth**.

**Discovery layer:** Continuous, **cited** signals from the outside world become **candidates**; humans (and later policy-gated automation) **promote** only what belongs in that truth. Nothing discovered silently overwrites the framework.

This roadmap answers how we move from a toy pipeline to that **operating model** at scale.

---

## End state (what “done” looks like)

### Product

- **Dual namespaces everywhere:** Official `AID-*` records and curated mappings are never confused with **candidate** records (IDs, labels, MCP tool names). No accidental equivalence.
- **Ingestion mesh:** Multiple **connector types** (taxonomy anchors, NVD/CVE with filters, GitHub advisories, vendor feeds, academic feeds with variance flags)—each with **allowlists**, rate limits, license posture, and **per-source metadata**.
- **Normalization:** Candidates carry a **stable schema**, **dedupe keys**, **citations**, **confidence**, and optional **extracted entities** (CVE, CWE, package, version ranges)—not only large unstructured summaries.
- **Correlation engine (mature):** Layered retrieval beyond raw BM25: lexical → optional embeddings → **explicit bridges** (e.g. CVE/CWE/product hints → tactic hints); outputs are **ranked hypotheses** with **explainability** (matched terms, shared IDs, overlap with `defendsAgainst` lines).
- **Review queue:** Triage workflow (statuses, rejection reasons, assignment), lightweight metrics (throughput, precision proxies), and **promotion** into `vendor/aidefense-framework/tactics/*.js` plus `node scripts/generate-dataset.js`.
- **Distribution:** Bundle the full MCP/REST service under `services/aidefend-mcp/` with optional, **strictly labeled** discovery tools (`search_discovery_candidates`, `explain_candidate_mapping`, etc.). Optional **Labs** or filtered web surfacing—policy decision with founder.

### Operations and trust

- **Governance:** Written **source policy**, **CC BY / redistribution** rules for summaries, **community-contributed** thresholds with **maintainer merge gate** on promotion.
- **Safety:** No automatic write to canonical `data.json`; **audit trail** on promotion; ingestion abuse considered (untrusted feed content).

### Evidence of value

Maintainers use the queue to **prioritize** taxonomy updates; integrators use MCP (and optionally the site) to separate **novel vs already mapped** hypotheses—with **calibrated** expectations (hypotheses, not ground truth).

---

## Phased roadmap

Work **phase-by-phase**; check items off in git as you go. Prefer **APIs and official downloads** over scraping where [`MAINTAINER_ALIGNMENT.md`](MAINTAINER_ALIGNMENT.md) already mandates it.

### Phase 0 — Current baseline

**Where we are:** Allowlisted RSS/Atom → **CandidateFinding** → BM25 vs flattened baseline → **GapReport** JSON ([`scripts/run_discovery_gap.py`](../../scripts/run_discovery_gap.py)).

**What it proves:** End-to-end plumbing and review-friendly artifacts.

**What it does not prove:** Reliable CVE ↔ technique semantics (BM25 is lexical similarity; threat-ID overlap only fires when IDs appear in text).

**Exit criteria:** Agreement that schemas and review vocabulary merit deeper investment.

#### Action items

- [x] Baseline loader over `data.json` (flatten `AID-*`, `defendsAgainst`, keywords).
- [x] Allowlisted RSS/Atom ingest + `CandidateFinding` JSONL append path.
- [x] BM25 gap reports + dated `reports/gap_run_*.json`.
- [x] Unit tests for baseline, BM25, RSS fixture parsing.
- [x] `REVIEW_CONTRACT`, `MAINTAINER_ALIGNMENT`, this roadmap.
- [ ] Document default **feed URLs** that 404 or drift; pin smoke-test feed in `lab/` README (ongoing hygiene).

---

### Phase 1 — Interpretable signal

**Goals:** Smaller, cleaner text for retrieval; entities and “why” for reviewers; measurable quality.

**Exit criteria:** Reviewers spend less time decoding blobs; **one credible “candidate ↔ defenses because …” story is demoed AND the resulting upstream promotion PR is merged into `aidefense-framework`.** Proving the report renders is not enough — the loop must close end-to-end, otherwise we cannot tell whether `is_gap` is producing things maintainers actually want. Promotion mechanics live in [`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md).

#### Action items

- [x] **Fetch + extract** for each `source_url`: **Trafilatura** on static HTML; cap body (`--body-max-kb`, default 48); `body_truncated` / `body_retrieval_truncated` flags (`scripts/aidefend_discovery/extract.py`, `run_discovery_gap.py`).
- [ ] **crawl4ai / Playwright path** — deferred (out of scope until needed); see [discovery note](discoveries/2026-05-02-web-extraction-pipeline.md).
- [x] **Dual fields:** `summary_raw`, `body_extracted`, `body_retrieval`, `retrieval_chunks` + `retrieval_chunk_queries` on candidates.
- [x] **Chunking** for retrieval queries; each chunk records `source_url`, `char_start` / `char_end`.
- [x] **Entity extraction v0:** CVE, GHSA, CWE via regex (`entities.py`); version-range regex still open.
- [x] **Explainability:** `GapReport.nearest_lexical_overlap_terms` (query∩doc tokens ranked by corpus IDF).
- [x] **Gold scaffold:** `lab/aidefend_discovery/gold/` + `scripts/eval_discovery_gold.py` (grow toward 20–50 labeled rows).
- [x] **NVD + GitHub Advisory API patterns** — enumerated in [discoveries/2026-05-02-nvd-ghsa-connector-api.md](discoveries/2026-05-02-nvd-ghsa-connector-api.md) (host WebFetch of official docs; re-validate with `/codex` workers if policy requires `crwl` primary captures).
- [x] **Promotion playbook** ([`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md)) — Shape A / Shape B mapping `CandidateFinding` → upstream tactic-object edits; soft pause lifted now that anchor diff has shipped. Phase 1 still exits on a **merged** upstream PR — open loop tracked in [`.ai/OPEN_LOOPS.md`](../../.ai/OPEN_LOOPS.md).

---

### Phase 2 — Correlation worth the name

**Goals:** Vuln-shaped hypotheses with explicit bridges, not only lexical neighbors.

**Exit criteria:** For vuln-shaped candidates, show **CVE + neighbor techniques + bridge rationale** more often than raw BM25 on release-note noise.

#### Action items

- [x] **NVD connector (Phase 2A baseline)** (official API JSON): parse CVE, CWE, descriptions; anonymous mode; incremental `lastMod*` windows + pagination + sqlite cursor checkpoint.
- [x] **NVD connector follow-up:** `NVD_API_KEY` auth + retry/backoff with jitter respecting `Retry-After` (Block A). Stricter AI-relevance/product allowlist tuning still open — tracked under embeddings rerank since they intersect.
- [x] **GHSA connector (Phase 2B):** `scripts/aidefend_discovery/ghsa_ingest.py` mirrors NVD pattern; `GH_PAT_FOR_GHSA` Bearer auth; cursor pagination via Link header; CVE↔GHSA join via `entities`; `--source ghsa` route.
- [x] **Bridge table v0:** CWE / ecosystem tags → suggested pillar/tactic **hints** (rules, not truth). Implemented in `scripts/aidefend_discovery/bridge.py` + `lab/aidefend_discovery/bridges/cwe_to_tactic.yaml` (26 CWEs with citations + per-entry confidence). Wired into `GapReport.bridge_rationales` / `suggested_pillars` / `suggested_phases` / `suggested_tactic_ids`.
- [ ] **Embeddings** over technique + `defendsAgainst` strings; optional **cross-encoder** rerank on BM25 top-20. **Re-open trigger fired (2026-05-03):** 25-row gold corpus eval shows `recall_is_gap=0.0` (out-of-scope detection broken). Active follow-up; see [Deferred with reasoning](#deferred-with-reasoning).
- [x] **Taxonomy anchor diff:** vendored YAMLs at `lab/aidefend_discovery/taxonomy_anchors/` (MITRE ATLAS, OWASP LLM/ML/Agentic, NIST AI 100-2, MAESTRO, SAIF, Databricks DASF, Cisco AITech) diffed against `data.json` defendsAgainst by `scripts/anchor_diff.py`. Emits `reports/anchor_diff_YYYYMMDD.json` with regression candidates. **Lifts the soft pause** on upstream promotions (see [`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md)) — reviewers consult the diff to confirm an anchor isn't already known under different wording before promoting.
- [ ] `/discover` pass on **STIX / MITRE CTI** consumption patterns if bridging to ATT&CK/ATLAS IDs.

---

### Phase 3 — Productized loop

**Exit criteria:** Weekly runs without babysitting one-off scripts.

#### Action items

- [x] **SQLite** at `lab/aidefend_discovery/discovery_state.db` — `state_store.py` v1 schema (runs / candidates / gap_reports / seen_window).
- [x] **Idempotent runs:** `INSERT OR IGNORE` on `content_hash`; sqlite cursor checkpoint per connector.
- [x] **Scheduler:** [`.github/workflows/discovery-nightly.yml`](../../.github/workflows/discovery-nightly.yml) (cron 09:00 UTC); `NVD_API_KEY` + `GH_PAT_FOR_GHSA` provisioned as repo secrets; opens auto-PR, never auto-merges.
- [x] **Review export:** [`scripts/export_review.py`](../../scripts/export_review.py) → CSV with `candidate_id`, `status`, `reject_reason`, `reviewer`, `source_urls`, `gap_summary`.
- [x] **Metrics:** [`scripts/discovery_metrics.py`](../../scripts/discovery_metrics.py) → JSON (% candidates with `is_gap`, throughput, promotion counts).

---

### Phase 4 — Ecosystem integration

**Exit criteria:** External consumers have a **documented contract** for “what might be missing” vs “what AIDEFEND officially says.”

#### Action items

- [x] **MCP/REST service:** `services/aidefend-mcp/app/discovery/store.py` (read-only sqlite client) + 3 namespace-walled tools (`search_discovery_candidates`, `explain_candidate_mapping`, `list_anchor_diff`); every response carries `discovery_namespace: true` + disclaimer; graceful "not configured" when `DISCOVERY_DB_PATH` unset.
- [x] **Contract tests:** 14 tests in `services/aidefend-mcp/tests/test_discovery_tools.py` assert `AID-*` IDs only appear in `references_aid` sidecar (never as primary IDs).
- [ ] **Public surface decision** with founder (site vs labs vs MCP-only); legal review if candidate text is shown verbatim. License-posture upgrade gated on this — see [Deferred with reasoning](#deferred-with-reasoning).

---

### Phase 5 — Maturity

#### Action items

- [x] Community PR path for **connector allowlists** and **threshold** defaults — `.github/PULL_REQUEST_TEMPLATE.md` (generic) + `.github/PULL_REQUEST_TEMPLATE/discovery_promotion.md` (upstream-promotion specialised) carry the audit-trail requirements.
- [x] Quarterly **quality audit** template — [`QUALITY_AUDIT_CHECKLIST.md`](QUALITY_AUDIT_CHECKLIST.md). Run is the maintenance ritual; output PR is `audit:Q<N>`.
- [ ] Scale (streaming, GPU embeddings) **only** if Phase 2 precision targets met (see "Deferred with reasoning" embeddings re-open trigger).

---

## Deferred with reasoning

These items were considered during a 2026-05-02 architecture review and consciously held. Each lists the **trigger that re-opens it**, so future-us doesn't relitigate the call.

- **`is_gap` two-trigger noise.** `max_bm25 < threshold` is noise-prone on release-note candidates, and `threat_ids_in_text_but_no_framework_line_overlap` fires too eagerly because upstream `defendsAgainst` paraphrases threats rather than embedding raw IDs. **Why deferred:** the rule is tunable, and Phase 2's CWE→tactic bridge reshapes it correctly. Tightening today without the bridge would just push false-positives around. **Re-open trigger:** Phase 2 bridge-table v0 begins.
- **BM25 vuln-shape mismatch.** Scoring CVE-style descriptions against defense-vocabulary text will reliably underperform — they live in different vocabularies. **Why deferred:** same Phase 2 fix; the architectural answer is the bridge table, not more retrieval sophistication. **Re-open trigger:** Phase 2 bridge-table v0 begins.
- **License posture (honor-system `license_note`).** Today `license_note` is free-text; there is a host allowlist for fetching but no classifier on stored body content. **Why deferred:** fine while bodies live only in `reports/` and are reviewer-local; the risk only crystallizes when candidate text is exposed via MCP or a public surface. **Re-open trigger:** any Phase 4 work toward MCP discovery tools or a public Labs surface.
- **Taxonomy drift.** A "novel" candidate that already exists in OWASP / MAESTRO / NIST under different wording would silently fork AIDEFEND vocabulary from its upstream anchors. **Resolved (2026-05-03):** Phase 2 anchor diff shipped — 9 vendored YAMLs in `lab/aidefend_discovery/taxonomy_anchors/` + `scripts/anchor_diff.py`. Soft pause on upstream promotions lifted in [`PROMOTION_PLAYBOOK.md`](PROMOTION_PLAYBOOK.md); pre-flight requires consulting the diff.
- **BM25 field weighting.** The baseline currently flattens technique `name + description + defendsAgainst` into one bag; field weights would let `defendsAgainst` matches count more or less than name matches once we trust `is_gap` enough to act on it. **Why deferred:** premature without gold rows to tune against. **Re-open trigger:** gold set reaches ~50 hand-labeled rows (currently 25 — partial) and `eval_discovery_gold.py` is in routine use.
- **Body cap / chunk budget alignment.** 48 KB body cap, 12 × 3.5 KB chunks ≈ 42 KB chunked content per doc. **Why deferred:** numbers already align; nothing to fix. **No re-open trigger** — only revisit if a new connector class needs longer bodies.

## How to use this document

| Phase   | Primary question |
|---------|------------------|
| 0 → 1 | Is the direction worth scaling? |
| 2     | Can we defend “correlation” for vuln-shaped intel? |
| 3 → 4 | Is it operable and shippable beside AIDEFEND? |
| 5     | Is it durable under community and maintainer load? |

Update this file when phases complete or priorities shift; link significant decisions in [`.ai/DECISIONS.md`](../../.ai/DECISIONS.md).
