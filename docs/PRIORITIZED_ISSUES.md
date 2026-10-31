# Private beta issue inventory — 28 October 2026

Scope: existing release reports, current scanner/security/worker/schema, CI, Render configuration, Neon connection state, comparison browser/API and local regression. This is a working inventory, not completion of the required fresh independent acceptance audit.

| Priority | Issue | State / next action |
|---|---|---|
| P0 | Confirmed cross-tenant/data-loss/authentication bypass | No confirmed issue in executed boundary tests; do not infer absence of vulnerabilities from this scope |
| P1 | Hosted request timeouts and unexplained historical review latency | Investigating; local repeated authentication reads reduced5→2; request/SQL diagnostics deployed at15504be; warm report/save medians0.271/0.313s but separate end-to-end scan/save14.635/8.282s did not improve |
| P1 | Hosted browser download verification | BLOCKED by cloud browser timeout; local Chromium download passed; retest hosted after diagnosing request path |
| P1 | Hosted responsive/manual accessibility acceptance | NOT TESTED; local viewport/axe checks do not substitute for hosted device coverage |
| P1 | Operational recovery/monitoring/retention | Synthetic restore passed; hosted isolated restore, alerts, retention enforcement and production rollback drill remain incomplete |
| P1 | Actual Render health-check configuration differs from Blueprint | Existing service reports empty HTTP health path (TCP probe); configure /health using supported authorized provider operation |
| P1 | Private repository integration and email-backed account workflows | Implementation/configuration incomplete; keep unavailable until real authorized provider tests succeed |
| P2 | Request and worker diagnostics / sensitive log minimization | Deployed and tested: generated request references, template-only structured logs, parameter hiding, successful-query timing, generic errors |
| P2 | Report comparison usability | Deployed core comparison; spacing improvement and diagnostics deployed; eight hosted API comparison checks passed |
| P2 | Rule support documentation and controlled-fixture expansion | Existing Python/OpenAPI tests pass; remaining config/migration/dependency/JS-TS rules require scoped implementation and tests |
| P2 | Core New Scan and account/team/review workflows | Existing CI/local suites pass; repeat full hosted acceptance after final candidate |
| P3 | PDF, advanced graph, AI explanation, broader commercial billing | Incomplete; do not imply supported execution, private access or live payment readiness |

Do not enable public registration or public launch. Do not execute customer source. Preserve all existing application data and schema0002 review tables. Use only existing Free infrastructure unless explicitly approved otherwise.


## Acceptance update — 29 October 2026

See [final acceptance](../PRIVATE_BETA_FINAL_ACCEPTANCE.md) for current evidence and remaining gates. Live application5e0e211 uses additive schema0003; retention defaults disabled, no live cleanup applied. In-app alerts are implemented; external outage alerts remain pending. CI restored sessions/static jobs and previous-source read compatibility passed; hosted recovery and actual service rollback remain untested. Provider HTTP healthCheckPath is still empty and requires the documented owner setting change.


## Recovery candidate — 29 October 2026

Candidate f8619a5 adds gated TLS email verification/recovery,hashed single-use tokens,pending-email provisioning,database-aware health and opt-in external monitor hooks;malformed credential comparisons fail closed. CI40804324589 passed. These changes are NOT deployed:staging stays5e0e211/schema0003. See [candidate](../PRIVATE_BETA_RELEASE_CANDIDATE.md),[integration configuration](EMAIL_AND_EXTERNAL_MONITORING.md),[recovery runbook](../RECOVERY_AND_ROLLBACK_RUNBOOK.md) and [remaining blockers](../REMAINING_BLOCKERS.md). No public launch or narrowed-scope approval is assumed.


## Private-source candidate — 29 October 2026

Candidate d52fead adds disabled-by-default per-repository fine-grained GitHub credentials,Fernet org/repository/version binding,owner controls,revision selection,immutable private static fetch and disconnect cancellation. CI40851366795 passed207 Python,108 PostgreSQL,67 browser and8 monitor checks plus recovery helpers. Migration0005 is not live;staging remains5e0e211/schema0003. Real private authorization,hosted acceptance,email/alert receipt and recovery remain blocked. Setup and limitations:[PRIVATE_GITHUB.md](PRIVATE_GITHUB.md). No GitHub App/OAuth or provider PAT revocation is claimed.
