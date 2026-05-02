# NVD API + GitHub Global Advisory API — connector design enumeration

Date: 2026-05-02  
Method: Host-side discover (WebFetch of official NIST + GitHub docs). **Not** a delegated `/codex` worker run; conclusions should be re-checked after any major API version change.

---

## Stage 1 — Framed question

| Field | Content |
|--------|---------|
| Subject | REST patterns for **NVD CVE 2.0** and **GitHub Security Advisories** suitable for discovery connectors |
| Context | `persistent-agent-security` Phase 2 roadmap; candidates today come from RSS + Trafilatura |
| Decision supported | Which endpoints, parameters, pagination, and auth to implement first; what to avoid |
| Assumptions | Read-only public data; no scraping HTML when JSON APIs exist; comply with NVD attribution and GitHub rate limits |

---

## Executive summary

**NVD** exposes a single well-documented **CVE 2.0 JSON** base URL with **offset pagination** (`startIndex`, `resultsPerPage` ≤ 2000), **mandatory paired date windows** for incremental sync (`lastModStartDate` / `lastModEndDate` or `pubStartDate` / `pubEndDate`, max **120 days** per range), and optional **`apiKey`** in headers (higher rate limit than anonymous). **GitHub** exposes **global** advisories at **`GET https://api.github.com/advisories`** with rich query filters (`ecosystem`, `cve_id`, `ghsa_id`, `cwes`, `affects`, EPSS fields, cursors) and detail at **`GET /advisories/{ghsa_id}`**; production use should prefer **authenticated** requests (much higher limits than **60/hour** unauthenticated). For connector enumeration, treat **NVD + GitHub global** as the two primary public legs; **org/repo advisory** REST is **permissioned** and only relevant when operating with a user/org token.

---

## Stage 3 — Comparison matrix (connector options)

| Criterion | NVD CVE 2.0 API | GitHub global `/advisories` | GitHub org `/orgs/{org}/security-advisories` |
|-----------|-----------------|----------------------------|-----------------------------------------------|
| Fit for public discovery | Excellent (authoritative CVE, CWE, CVSS, CPE, KEV flags) | Excellent (package ecosystems, GHSA↔CVE, EPSS on records) | Org-scoped; needs owner/security manager + token scopes |
| Base URL / path | `https://services.nvd.nist.gov/rest/json/cves/2.0` | `https://api.github.com/advisories` | `https://api.github.com/orgs/{org}/security-advisories` |
| Auth | Optional `apiKey` request header (case-sensitive value) | `Authorization: Bearer` + `Accept: application/vnd.github+json` + `X-GitHub-Api-Version` (per docs) | Same + org permission |
| Pagination | `startIndex` + `resultsPerPage` (default tuned; max 2000) | Cursor `before` / `after`, `per_page` ≤ 100 | Cursor + `per_page` |
| Incremental sync | `lastModStartDate` + `lastModEndDate` (paired; ≤120d range); or `pubStartDate`/`pubEndDate` | `updated` / `published` / `modified` query filters (doc date-range syntax) | `sort` created/updated/published |
| AI-relevant filters | `keywordSearch` (+ optional `keywordExactMatch`), `cweId`, `cpeName` + `isVulnerable`, `hasKev`, `kevStartDate`/`kevEndDate`, CVSS severity/metrics | `ecosystem` (`pip`, `npm`, `go`, `maven`, …), `cve_id`, `cwes`, `affects` (package list cap 1000), `severity`, EPSS params | State filter `triage`/`draft`/`published`/`closed` |
| Rate / abuse | 5 req / 30s without key; **50 req / 30s** with key; NIST recommends ~**6s sleep** between requests | **60 req/hr** unauthenticated; **5,000 req/hr** authenticated (user PAT); secondary limits (concurrency, points/min) | Same as authenticated user/app |
| Best for | CVE ground truth, KEV, CWE bridges | OSS dependency advisories tied to ecosystems | Private triage pipelines inside an org |
| Avoid when | You need GHSA-specific metadata without calling GitHub | You rely only on unauthenticated high-volume polling | Building a public “discovery” feed without org access |

---

## Stage 4 — Gap analysis (current prototype vs APIs)

### Gap: No structured vuln ingest

- **Current:** Regex CVE/GHSA on RSS text only.  
- **Better approach:** Dedicated connectors emitting the same **`CandidateFinding`** shape with `source_type` + stable ids (`cve_id`, `ghsa_id`) from API JSON.  
- **Impact:** High | **Effort:** Medium  
- **Source:** [NVD CVE API](https://nvd.nist.gov/developers/vulnerabilities), [GitHub global advisories](https://docs.github.com/en/rest/security-advisories/global-advisories)

### Gap: NVD sync without blowing rate limits

- **Current:** N/A.  
- **Better approach:** Store cursor = last `lastModEndDate` processed; windows ≤120 days; exponential backoff on 403/429; optional bulk initial load via [NVD API workflows](https://nvd.nist.gov/developers/api-workflows) guidance.  
- **Impact:** High | **Effort:** Low  
- **Source:** [NVD Start Here — rate limits & maintenance](https://nvd.nist.gov/developers/start-here)

### Gap: Joining GHSA ↔ NVD narrative

- **Current:** Textual overlap only.  
- **Better approach:** If `cve_id` present on GitHub advisory, attach both identifiers on the candidate; use NVD `cveId` filter for enrichment pass.  
- **Impact:** Medium | **Effort:** Low  
- **Source:** GitHub advisory schema (`cve_id` field) in global advisories doc

---

## Connector enumeration (implementable list)

### C1 — NVD incremental (recommended first)

- **Request:** `GET .../cves/2.0?lastModStartDate=...&lastModEndDate=...` (+ optional `resultsPerPage`, `startIndex`).  
- **Emit:** one candidate per CVE (or per changed CVE) with description text, CWE list, references URLs, `hasKev` from response flags.  
- **Compliance:** Display [NVD non-endorsement notice](https://nvd.nist.gov/developers/start-here) in app/docs.

### C2 — NVD keyword slice (AI vocabulary)

- **Request:** `keywordSearch=...` (URL-encode spaces); optional `keywordExactMatch`.  
- **Risk:** Keyword semantics are CNA description text—not NVD editorial control ([NVD CVE API doc](https://nvd.nist.gov/developers/vulnerabilities)).  
- **Use:** Narrow scheduled jobs (e.g. “PyTorch”, “LangChain”, “ONNX”, “CUDA”).

### C3 — NVD KEV slice

- **Request:** `?hasKev` with optional `kevStartDate` + `kevEndDate` (both required when using KEV dates).  
- **Use:** High-priority candidate queue.

### C4 — GitHub global list (ecosystem-scoped)

- **Request:** `GET /advisories?ecosystem=pip&sort=updated&direction=desc&per_page=100` (+ cursor).  
- **Emit:** candidates with `ghsa_id`, `summary`/`description`, `vulnerabilities[].package`, version ranges, `cwes`, `cve_id`.  
- **Auth:** PAT in CI secret; respect `x-ratelimit-*` headers ([GitHub rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)).

### C5 — GitHub global by CVE or GHSA

- **Request:** `GET /advisories?cve_id=CVE-...` or `GET /advisories/{GHSA}`.  
- **Use:** Enrichment when RSS/regression mentions a specific id.

### C6 — Org repository advisories (optional, token-gated)

- **Request:** `GET /orgs/{org}/security-advisories` ([repo advisories REST](https://docs.github.com/en/rest/security-advisories/repository-advisories)).  
- **Use:** Only when the operator owns the org; not part of the public “open discovery” default.

---

## Quick wins (implementation order)

1. **Secrets + notice:** `NVD_API_KEY`, `GITHUB_TOKEN`; ship NVD attribution string in README/CLI help.  
2. **C4 + C5:** GitHub global list with `ecosystem` in `{pip, npm, go}` + detail fetch for top N.  
3. **C1:** NVD `lastMod` sliding window + sqlite cursor.  
4. **C3:** Weekly KEV pass.  
5. **Join:** Merge C5 + C1 when `cve_id` present.

---

## Strategic investments

- Local **SQLite** tables: `nvd_cursor`, `ghsa_cursor`, raw JSON blobs (dedupe by id).  
- **EPSS** fields already on GitHub advisory JSON—use for ranking, not as sole “gap” truth.  
- **CPE-based** NVD queries (`cpeName` + `isVulnerable`) once you maintain a curated CPE list for ML runtimes (later phase).

---

## Nice-to-have

- Conditional requests (`If-None-Match`) where GitHub supports ETag on advisories (verify per endpoint behavior in implementation).  
- NVD **sourceIdentifier** filtering for CNA-of-interest slices.

---

## Disregard list (do not prioritize)

- Scraping the NVD or GitHub **HTML** vulnerability pages for core fields when JSON APIs return the same data.  
- Unauthenticated GitHub polling at volumes above **60/hr**.  
- Full unfiltered NVD history pulls without `startIndex` paging + backoff (will trip firewall/rate rules per NIST docs).  
- Assuming **GitHub-reviewed** vs **unreviewed** advisory types are interchangeable without checking the `type` field (global list defaults exclude malware unless `type=malware` per docs).

---

## Sources (consulted)

| Source | Contribution |
|--------|----------------|
| [NVD — Start Here](https://nvd.nist.gov/developers/start-here) | JSON/REST model, `apiKey` header, rate limits (5/30s vs 50/30s), UTF-8/ISO-8601, attribution notice, maintenance windows (≤2h automation recommendation), 6s sleep guidance. |
| [NVD — CVE API 2.0](https://nvd.nist.gov/developers/vulnerabilities) | Base URL, `cveId`, `cweId`, `keywordSearch`, `hasKev`, date pairs (`lastMod*`, `pub*`, `kev*`), `startIndex`/`resultsPerPage` (max 2000), CPE/`isVulnerable`, CVSS filters. |
| [GitHub — Global security advisories REST](https://docs.github.com/en/rest/security-advisories/global-advisories) | List + get endpoints, query parameters, response schema (identifiers, vulnerabilities[], EPSS, CWE). |
| [GitHub — Repository/org security advisories REST](https://docs.github.com/en/rest/security-advisories/repository-advisories) | Permissioned org listing; scope requirements. |
| [GitHub — Rate limits for REST](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) | 60/hr unauthenticated vs 5k/hr authenticated; secondary limits; retry guidance. |

### Consulted but rejected for primary design

- **GraphQL-only** advisory workflows for v1 connectors (REST already covers global enumeration; GraphQL adds complexity unless you need fields absent from REST).  
- **Firecrawl / third-party scrapers** for NVD/GitHub primary fields (APIs are authoritative and ToS-friendlier).

---

## Contradictions / humility

- GitHub documents **`X-GitHub-Api-Version`**; pin and update deliberately.  
- NVD `keywordSearch` behavior (AND of tokens, wildcard suffix per doc) can surprise operators—validate with sample queries before embedding in “AI” product copy.  
- EPSS on GitHub responses is useful for **prioritization**, not for claiming framework “gaps” alone.
