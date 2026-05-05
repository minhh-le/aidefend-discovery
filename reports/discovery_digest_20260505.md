# AIDEFEND Discovery Public Review Digest

## Run Summary

- Candidates analyzed: 5
- Candidates shown in detail: 5
- Number in lowest coverage view: 5
- Number in highest severity view: 5
- Source counts: ghsa_api: 5
- Generated timestamp: 2026-05-05T22:24:48Z
- Input report path: reports/gap_run_20260505.json
- Source: ghsa

## Lowest Coverage Candidates

| Rank | Candidate | Coverage Score | Security Score | Recommended Action |
| ---: | --- | ---: | ---: | --- |
| 1 | GHSA-6h2x-4gjf-jc5w | 100/100 | 100/100 | Merge Into Existing |
| 2 | GHSA-f6p5-76fp-m248 | 100/100 | 100/100 | Merge Into Existing |
| 3 | GHSA-mv2r-q4g5-j8q5 | 100/100 | 100/100 | Merge Into Existing |
| 4 | GHSA-q2fj-6h62-59m2 | 100/100 | 100/100 | Merge Into Existing |
| 5 | GHSA-xq3c-8gqm-v648 | 100/100 | 100/100 | Merge Into Existing |

## Highest Severity Candidates

| Rank | Candidate | Security Score | Coverage Score | Recommended Action |
| ---: | --- | ---: | ---: | --- |
| 1 | GHSA-6h2x-4gjf-jc5w | 100/100 | 100/100 | Merge Into Existing |
| 2 | GHSA-f6p5-76fp-m248 | 100/100 | 100/100 | Merge Into Existing |
| 3 | GHSA-mv2r-q4g5-j8q5 | 100/100 | 100/100 | Merge Into Existing |
| 4 | GHSA-q2fj-6h62-59m2 | 100/100 | 100/100 | Merge Into Existing |
| 5 | GHSA-xq3c-8gqm-v648 | 100/100 | 100/100 | Merge Into Existing |

## Candidate Briefs

### GHSA-6h2x-4gjf-jc5w

- Coverage Score: 100/100
- Security Score: 100/100
- Recommended Action: Merge Into Existing

#### Reviewer Decision Checklist

- [ ] Confirm this is AI/security relevant.
- [ ] Confirm whether the nearest AIDEFEND techniques already cover the behavior.
- [ ] Confirm whether source identifiers and affected package/version evidence are sufficient.
- [ ] Record promote, merge, reject, needs-evidence, or monitor decision.

#### What This Is

autogluon.multimodal vulnerable to unsafe YAML deserialization ### Impact A potential unsafe deserialization issue exists within the `autogluon.multimodal` module, where YAML files are loaded via `yaml.load()` instead of `yaml.safe_load()`. The deserialization of untrusted data may allow an unprivileged third party to cause remote code execution, denial of service, and impact to both confidentiality and integrity. Impacted versions: `>=0.4.0;<0.4.3`, `>=0.5.0;<0.5.2`. ### Patches The patches are included in `autogluon.multimodal==0.4.3`, `autogluon.multimodal==0.5.2` and Deep Learning Containers `0.4.3` and `0.5.2`. ### Workarounds Do not load data which originated from an untrusted sourc...

#### Why AIDEFEND Should Care

CWE-502: Deserialization of untrusted data — pickle attacks on model weights, joblib/numpy artifacts; harden via safetensors, isolate load context. (conf 0.85; src https://cwe.mitre.org/data/definitions/502.html)

#### Coverage Assessment

High coverage (100/100). Review whether this should merge into existing techniques: AID-H-031.004, AID-M-009, AID-H-031, AID-H-032, AID-E-004.

#### Security Assessment

Severity basis: high. Security Score 100/100 includes deterministic boosts for reviewed source metadata and observed identifiers/package/version evidence.

#### Evidence

- Identifiers: CVE=CVE-2017-18342; GHSA=ghsa-6h2x-4gjf-jc5w; CWE=CWE-502
- Affected packages / versions: packages=pip:autogluon.multimodal; versions=vulnerable:>= 0.4.0, < 0.4.3, vulnerable:>= 0.5.0, < 0.5.2, >= 0.4.0, < 0.4.3, >= 0.5.0, < 0.5.2, == 0.4.3, == 0.5.2, 2017 - 18342
- Source URLs: https://github.com/awslabs/autogluon/security/advisories/GHSA-6h2x-4gjf-jc5w, https://github.com/awslabs/autogluon/pull/1987, https://github.com/awslabs/autogluon/commit/23a37e74e58d03055c84a1b89c5af6c3db296b5e, https://github.com/advisories/GHSA-6h2x-4gjf-jc5w
- Bridge rationales: CWE-502: Deserialization of untrusted data — pickle attacks on model weights, joblib/numpy artifacts; harden via safetensors, isolate load context. (conf 0.85; src https://cwe.mitre.org/data/definitions/502.html)
- Nearest technique IDs: AID-H-031.004, AID-M-009, AID-H-031, AID-H-032, AID-E-004

#### Backend Provenance

- Candidate ID: candidate-rss-757a8b9dcc4c0174
- Source type: ghsa_api
- Source ID: GHSA-6h2x-4gjf-jc5w
- Retrieved at: 2026-05-05T22:24:48Z
- Raw score details: max_bm25=67.41338016772193; gap_bm25_max=8.0; bm25_scores=67.41338016772193, 51.71999182524109, 47.4229313257627, 44.26939754790622, 43.66880137934864
- Gap reason: not_gap
- Producer confidence: 0.75
- License note: GitHub Security Advisory; CC BY 4.0 per GitHub Advisory Database; verify package vendor source for redistribution scope.

### GHSA-f6p5-76fp-m248

- Coverage Score: 100/100
- Security Score: 100/100
- Recommended Action: Merge Into Existing

#### Reviewer Decision Checklist

- [ ] Confirm this is AI/security relevant.
- [ ] Confirm whether the nearest AIDEFEND techniques already cover the behavior.
- [ ] Confirm whether source identifiers and affected package/version evidence are sufficient.
- [ ] Record promote, merge, reject, needs-evidence, or monitor decision.

#### What This Is

URL Rewrite vulnerability in multiple zendframework components zend-diactoros (and, by extension, Expressive), zend-http (and, by extension, Zend Framework MVC projects), and zend-feed (specifically, its PubSubHubbub sub-component) each contain a potential URL rewrite exploit. In each case, marshaling a request URI includes logic that introspects HTTP request headers that are specific to a given server-side URL rewrite mechanism. When these headers are present on systems not running the specific URL rewriting mechanism, the logic would still trigger, allowing a malicious client or proxy to emulate the headers to request arbitrary content.

#### Why AIDEFEND Should Care

The source carries enough security signal to review as supporting evidence for AIDEFEND coverage.

#### Coverage Assessment

High coverage (100/100). Review whether this should merge into existing techniques: AID-H-029.004, AID-H-020.001, AID-H-029, AID-E-004, AID-H-020.

#### Security Assessment

Severity basis: high. Security Score 100/100 includes deterministic boosts for reviewed source metadata and observed identifiers/package/version evidence.

#### Evidence

- Identifiers: CVE=None observed; GHSA=ghsa-f6p5-76fp-m248; CWE=None observed
- Affected packages / versions: packages=composer:zendframework/zend-diactoros, composer:zendframework/zend-feed, composer:zendframework/zend-http; versions=vulnerable:< 1.8.4, vulnerable:< 2.10.3, vulnerable:< 2.8.1
- Source URLs: https://github.com/FriendsOfPHP/security-advisories/blob/master/zendframework/zend-diactoros/ZF2018-01.yaml, https://github.com/FriendsOfPHP/security-advisories/blob/master/zendframework/zend-feed/ZF2018-01.yaml, https://github.com/FriendsOfPHP/security-advisories/blob/master/zendframework/zend-http/ZF2018-01.yaml, https://github.com/advisories/GHSA-f6p5-76fp-m248
- Bridge rationales: None observed
- Nearest technique IDs: AID-H-029.004, AID-H-020.001, AID-H-029, AID-E-004, AID-H-020

#### Backend Provenance

- Candidate ID: candidate-rss-2c4acdae94589bfd
- Source type: ghsa_api
- Source ID: GHSA-f6p5-76fp-m248
- Retrieved at: 2026-05-05T22:24:48Z
- Raw score details: max_bm25=42.35252596984861; gap_bm25_max=8.0; bm25_scores=42.35252596984861, 39.7839530442546, 38.97643421628365, 37.23000543103646, 37.146900325537125
- Gap reason: not_gap
- Producer confidence: 0.75
- License note: GitHub Security Advisory; CC BY 4.0 per GitHub Advisory Database; verify package vendor source for redistribution scope.

### GHSA-mv2r-q4g5-j8q5

- Coverage Score: 100/100
- Security Score: 100/100
- Recommended Action: Merge Into Existing

#### Reviewer Decision Checklist

- [ ] Confirm this is AI/security relevant.
- [ ] Confirm whether the nearest AIDEFEND techniques already cover the behavior.
- [ ] Confirm whether source identifiers and affected package/version evidence are sufficient.
- [ ] Record promote, merge, reject, needs-evidence, or monitor decision.

#### What This Is

Denial of service in ASP.NET Core A denial of service vulnerability exists when OData Library improperly handles web requests, aka "OData Denial of Service Vulnerability." This affects Microsoft.Data.OData.

#### Why AIDEFEND Should Care

The source carries enough security signal to review as supporting evidence for AIDEFEND coverage.

#### Coverage Assessment

High coverage (100/100). Review whether this should merge into existing techniques: AID-E-004, AID-M-003.002, AID-I-003, AID-I-001.001, AID-I-001.002.

#### Security Assessment

Severity basis: high. Security Score 100/100 includes deterministic boosts for reviewed source metadata and observed identifiers/package/version evidence.

#### Evidence

- Identifiers: CVE=CVE-2018-8269; GHSA=ghsa-mv2r-q4g5-j8q5; CWE=None observed
- Affected packages / versions: packages=nuget:Microsoft.Data.OData, nuget:Microsoft.AspNetCore.All, nuget:Microsoft.AspNetCore.DataProtection.AzureStorage; versions=vulnerable:< 5.8.4, vulnerable:>= 2.1.0, < 2.1.13, vulnerable:>= 2.2.0, < 2.2.7
- Source URLs: https://nvd.nist.gov/vuln/detail/CVE-2018-8269, https://github.com/advisories/GHSA-mv2r-q4g5-j8q5, https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/CVE-2018-8269, https://www.exploit-db.com/exploits/46101/, https://github.com/aspnet/Announcements/issues/385, https://github.com/github/advisory-database/issues/302
- Bridge rationales: None observed
- Nearest technique IDs: AID-E-004, AID-M-003.002, AID-I-003, AID-I-001.001, AID-I-001.002

#### Backend Provenance

- Candidate ID: candidate-rss-b2dde02fc10412d0
- Source type: ghsa_api
- Source ID: GHSA-mv2r-q4g5-j8q5
- Retrieved at: 2026-05-05T22:24:48Z
- Raw score details: max_bm25=33.53605081590169; gap_bm25_max=8.0; bm25_scores=33.53605081590169, 24.9268074283872, 22.89116418605699, 22.249510598704425, 21.53815575090868
- Gap reason: not_gap
- Producer confidence: 0.75
- License note: GitHub Security Advisory; CC BY 4.0 per GitHub Advisory Database; verify package vendor source for redistribution scope.

### GHSA-q2fj-6h62-59m2

- Coverage Score: 100/100
- Security Score: 100/100
- Recommended Action: Merge Into Existing

#### Reviewer Decision Checklist

- [ ] Confirm this is AI/security relevant.
- [ ] Confirm whether the nearest AIDEFEND techniques already cover the behavior.
- [ ] Confirm whether source identifiers and affected package/version evidence are sufficient.
- [ ] Record promote, merge, reject, needs-evidence, or monitor decision.

#### What This Is

Apiman Vert.x Gateway has Transitive Hazelcast connection caching issue ### Impact If you are using the **Apiman Vert.x Gateway** prior to Apiman 3.0.0.Final, a connection caching issue in Hazelcast could allow an unauthenticated, remote attacker to access and manipulate data in the cluster with another authenticated connection's identity. Hazelcast is a transitive dependency of the Apiman Vert.x Gateway. The precise risk is difficult to quantify at this juncture as plugins deployed by users may make use of Hazelcast in a different manner to the main Apiman codebase. If any of your custom Apiman plugins specify Hazelcast dependencies, you should also bump these versions. Hint: an easy way...

#### Why AIDEFEND Should Care

The source carries enough security signal to review as supporting evidence for AIDEFEND coverage.

#### Coverage Assessment

High coverage (100/100). Review whether this should merge into existing techniques: AID-M-009, AID-H-029.001, AID-H-034.001, AID-H-025.004, AID-H-034.

#### Security Assessment

Severity basis: high. Security Score 100/100 includes deterministic boosts for reviewed source metadata and observed identifiers/package/version evidence.

#### Evidence

- Identifiers: CVE=None observed; GHSA=ghsa-q2fj-6h62-59m2, ghsa-c5hg-mr8r-f6jp; CWE=None observed
- Affected packages / versions: packages=maven:io.apiman:apiman-gateway-platforms-vertx, maven:io.apiman:apiman-distro-vertx; versions=vulnerable:< 3.0.0.Final
- Source URLs: https://github.com/apiman/apiman/security/advisories/GHSA-q2fj-6h62-59m2, https://github.com/advisories/GHSA-c5hg-mr8r-f6jp, https://support.hazelcast.com/s/article/Security-Advisory-for-CVE-2022-36437, https://github.com/advisories/GHSA-q2fj-6h62-59m2
- Bridge rationales: None observed
- Nearest technique IDs: AID-M-009, AID-H-029.001, AID-H-034.001, AID-H-025.004, AID-H-034

#### Backend Provenance

- Candidate ID: candidate-rss-7f699a2646a9ba54
- Source type: ghsa_api
- Source ID: GHSA-q2fj-6h62-59m2
- Retrieved at: 2026-05-05T22:24:48Z
- Raw score details: max_bm25=99.81640782085873; gap_bm25_max=8.0; bm25_scores=99.81640782085873, 53.2144770270592, 48.11284509304677, 47.26646552301954, 45.669501985866376
- Gap reason: not_gap
- Producer confidence: 0.75
- License note: GitHub Security Advisory; CC BY 4.0 per GitHub Advisory Database; verify package vendor source for redistribution scope.

### GHSA-xq3c-8gqm-v648

- Coverage Score: 100/100
- Security Score: 100/100
- Recommended Action: Merge Into Existing

#### Reviewer Decision Checklist

- [ ] Confirm this is AI/security relevant.
- [ ] Confirm whether the nearest AIDEFEND techniques already cover the behavior.
- [ ] Confirm whether source identifiers and affected package/version evidence are sufficient.
- [ ] Record promote, merge, reject, needs-evidence, or monitor decision.

#### What This Is

async-graphql / async-graphql - @DOS GraphQL Nested Fragments overflow ### Impact Executing deeply nested queries may cause stack overflow. ### Patches Upgrade to `v4.0.6`

#### Why AIDEFEND Should Care

The source carries enough security signal to review as supporting evidence for AIDEFEND coverage.

#### Coverage Assessment

High coverage (100/100). Review whether this should merge into existing techniques: AID-I-003, AID-I-008.002, AID-D-005.007, AID-D-005, AID-H-031.004.

#### Security Assessment

Severity basis: high. Security Score 100/100 includes deterministic boosts for reviewed source metadata and observed identifiers/package/version evidence.

#### Evidence

- Identifiers: CVE=None observed; GHSA=ghsa-xq3c-8gqm-v648; CWE=None observed
- Affected packages / versions: packages=rust:async-graphql; versions=vulnerable:< 4.0.6
- Source URLs: https://github.com/async-graphql/async-graphql/security/advisories/GHSA-xq3c-8gqm-v648, https://github.com/async-graphql/async-graphql/commit/521769b80039fc8043d1c9883e3d6e5b57359072, https://rustsec.org/advisories/RUSTSEC-2022-0037.html, https://github.com/advisories/GHSA-xq3c-8gqm-v648
- Bridge rationales: None observed
- Nearest technique IDs: AID-I-003, AID-I-008.002, AID-D-005.007, AID-D-005, AID-H-031.004

#### Backend Provenance

- Candidate ID: candidate-rss-11550f45659fad9a
- Source type: ghsa_api
- Source ID: GHSA-xq3c-8gqm-v648
- Retrieved at: 2026-05-05T22:24:48Z
- Raw score details: max_bm25=13.971497970953962; gap_bm25_max=8.0; bm25_scores=13.971497970953962, 12.875898605943036, 12.066746920080094, 9.16922171133748, 9.120611199489211
- Gap reason: not_gap
- Producer confidence: 0.75
- License note: GitHub Security Advisory; CC BY 4.0 per GitHub Advisory Database; verify package vendor source for redistribution scope.

## Methodology / Provenance Appendix

- Input source is one deterministic `gap_run_*.json` report, not sqlite backlog/history.
- Coverage Score is `round(min(100, 100 * max_bm25 / gap_bm25_max))` using the run threshold.
- Security Score starts from advisory severity and adds bounded evidence boosts for reviewed source, CVE, GHSA, CWE, and package/version evidence.
- Recommended actions are deterministic reviewer triage labels. They are not upstream AIDEFEND truth.
- Raw provenance remains in each candidate brief: source URL, source type, candidate ID, retrieved timestamp, identifiers, and raw score details.
