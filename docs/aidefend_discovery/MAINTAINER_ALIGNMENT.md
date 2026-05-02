# Maintainer alignment (recorded decisions)

**Source:** R&D plan thread + explicit annotations for implementation. Use this until superseded by founder/maintainer docs.

| Topic | Decision |
|-------|-----------|
| **Ingestion scope** | Prioritize **official, versioned** taxonomy anchors (MITRE ATLAS, OWASP LLM/ML/Agentic, MAESTRO, NIST AML, SAIF, DASF, Cisco AI framework), **MITRE CTI-style** feeds where IDs are stable, **NVD/CVE/CISA KEV** for vuln-shaped facts (AI-adjacent filtering), **vendor bulletins** for gaps, **GitHub Security Advisories** for OSS ML/agent stacks, **standards/regulator drafts** for control-gap detection, **arXiv/cs.CR** (etc.) as **candidate-only** unless corroborated, **bug bounty** aggregates optional/noisy. |
| **Taxonomy authority** | When wording conflicts with upstream frameworks, **AIDEFEND** is canonical for narrative synthesis; still cite upstream IDs faithfully in mappings. |
| **Overlap thresholds** | **Community-contributable** tuning (BM25 / gap flags); maintainers retain merge gate for promotion. |
| **MCP** | **Extend** existing [aidefend-mcp](https://github.com/edward-playground/aidefend-mcp) with **optional**, strictly labeled discovery tools (do not present candidates as approved `AID-*` facts). |
| **Product surface for candidates** | **Open** — confirm shipping channel (`aidefend.net` vs labs vs MCP-only) per release planning. |
| **CC BY / licensing** | Summaries must respect third-party terms; default ingestion disclaimer applies; no verbatim bulk copying without license check (**confirm with founder** for redistribution boundaries). |

Prototype implementation in this repo stays **read-only** vs aidefense-framework data and does **not** auto-promote.
