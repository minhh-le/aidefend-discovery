# Gold labeling log — 2026-05-03

Source: 25 candidates from authenticated NVD + GHSA pulls, windows
**2026-04-15 → 2026-05-01** (NVD `lastMod`) and **2026-04-15 → present**
(GHSA `updated_at`), severity-high GHSA filter, `machine learning` NVD
keyword. Reviewer: `claude-opus-4-7` (Architecture-Edit session). All
labels are auditable via the `rationale` field in `example_labels.jsonl`.

## Eval result against this corpus (BM25 default threshold 8.0, no
embeddings, anchor-diff-aware bridge active)

```json
{
  "gold_rows_used": 25,
  "is_gap_accuracy": 0.76,
  "nearest_topk_hit_rate": 1.0,
  "is_gap_confusion": {"tp": 0, "fp": 0, "fn": 6, "tn": 19},
  "precision_is_gap": null,
  "recall_is_gap": 0.0,
  "f1_is_gap": null
}
```

**Honest read:**
- Top-k retrieval is perfect (1.0) — when the system maps a candidate to
  an AID-* tactic family, it picks one a reviewer agrees with.
- `is_gap_accuracy` at 0.76 looks fine but masks a *recall=0* problem:
  the system catches **none** of the 6 genuine gaps. All BM25 scores on
  out-of-scope candidates were >> 8.0 (`max_bm25` 21–163) so the
  threshold-only `is_gap` rule never fires. **Re-open trigger for
  embeddings + cross-encoder rerank: this is the precision plateau
  predicted in ROADMAP "Deferred with reasoning."**
- The right Phase-2 fix is *not* a higher BM25 threshold (would lose
  recall on genuine gaps with high lexical overlap) — it's an
  **out-of-scope classifier** layered before BM25, or a cross-encoder
  rerank that downweights non-AI matches.

## Per-row summary

| # | source_id | expect_is_gap | nearest hint | one-line rationale |
|---|---|---|---|---|
| 1  | GHSA-324q-cwx9-7crr | false | AID-H | KubeAI ollama startup probe shell injection (CWE-78) — covered by harden tactic |
| 2  | GHSA-4xqg-gf5c-ghwq | **true** |  | MCP-server-K8s argument injection — MCP-protocol-specific; AIDEFEND lacks MCP-tool-call hardening guidance |
| 3  | GHSA-3jr7-6hqp-x679 | false | AID-H | Mesop WebSocket DoS (CWE-400) — DoS hardening covered |
| 4  | CVE-2024-34073 | false | AID-M-009 | sagemaker-python-sdk command injection — covered |
| 5  | CVE-2024-49375 | false | AID-M-009 | Rasa malicious-model RCE (pickle) — directly covered |
| 6  | CVE-2024-6960 | false | AID-M-009 | CWE-502 deserialization in AI/ML — covered |
| 7  | CVE-2024-34072 | false | AID-M | CWE-502 in AI/ML stack — covered |
| 8  | CVE-2024-40441 | false | AID-M-009 | Doccano SSRF privesc — covered |
| 9  | CVE-2024-40442 | false | AID-H-019 | Doccano CWE-94 code injection — covered |
| 10 | CVE-2025-54430 | false | AID-M-009 | AI/ML CWE-78 — covered |
| 11 | CVE-2025-62376 | false | AID-M-009 | CWE-287 auth on AI/ML service — covered |
| 12 | CVE-2026-34445 | false | AID-M-009 | CWE-20+CWE-400+CWE-915 cluster — covered |
| 13 | GHSA-2mvx-f5qm-v2ch | **true** |  | WordPress 'My Calendar' IDOR — out_of_scope; BM25 score 163 over-confident |
| 14 | GHSA-3382-gw9x-477v | **true** |  | Weblate (translation) privilege issue — out_of_scope |
| 15 | GHSA-4v48-4q5m-8vx4 | false | AID-M-009 | Prometheus auth (often paired with AI obs) — covered |
| 16 | GHSA-8wfp-579w-6r25 | false | AID-M-009 | Kyverno K8s policy info exposure — covered |
| 17 | GHSA-f38f-5xpm-9r7c | **true** |  | CairoSVG DoS — only AI-relevant if used in doc-ingest; conservatively out_of_scope |
| 18 | GHSA-fpx9-9hq8-w2xc | false | AID-I-002 | Krayin CRM SSRF — defensive pattern AID-I-002 covers SSRF egress |
| 19 | GHSA-ggmw-mjhv-75rm | **true** |  | Random Go shopping-cart command injection — out_of_scope |
| 20 | GHSA-hv99-mxm5-q397 | **true** |  | Weblate path-traversal + info-exposure — out_of_scope |
| 21 | GHSA-jjf9-w5vj-r6vp | false | AID-M-009 | Erlang Ash unbounded resource — borderline AI-relevant, mark covered |
| 22 | GHSA-x4p7-7chp-64hq | false | AID-H-004 | Keycloak missing-auth (fronts AI services) — covered |
| 23 | GHSA-wmxr-6j5f-838p | false | AID-D | Keycloak SAML adapter improper authn — detect tactic |
| 24 | CVE-2024-49361 | false | AID-E-004 | AI/ML CWE-20 input val — covered, AID-E response is reasonable |
| 25 | CVE-2026-34447 | false | AID-M-009 | AI/ML path-traversal cluster — covered |

## Methodology notes

- **Labeling source:** I read each candidate's title and summary, then
  the BM25 top-5 nearest_technique_ids and their concise descriptions
  via the gap report. For borderline cases (Prometheus, Erlang Ash,
  Keycloak), I labeled `expect_is_gap=false` only when the candidate's
  defensive pattern is *general enough* that AID-* harden/detect/isolate
  techniques actually apply, even if the package itself isn't AI-specific.
- **Out-of-scope criterion (genuine gap):** if AIDEFEND has no plausible
  defendsAgainst extension that wouldn't dilute the framework's AI-defense
  focus, I labeled it as a gap. This is conservative — a stricter labeling
  would mark more general-OSS items as gaps.
- **Confidence:** all labels are `claude-opus-4-7` 2026-05-03; rationales
  are concise; verify before promotion. The class-balance imbalance
  (19/6) is intentional — most NVD/GHSA AI-keyword pulls in this window
  surfaced legitimately AI-relevant items.

## What I did NOT label

- **Bridge rationale quality:** the bridge produces sensible outputs on
  every candidate I inspected, but evaluating bridge precision needs a
  separate per-CWE label set (not in this commit).
- **Promotion shape (A vs B):** these labels are about gap-detection
  precision, not promotion mechanics. Promotion-shape evaluation lives
  in `PROMOTION_PLAYBOOK.md`.
