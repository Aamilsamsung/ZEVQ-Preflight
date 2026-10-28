# Private beta issue inventory — 28 October 2026

Scope: existing release reports, current scanner/security/worker/schema, CI, Render configuration, Neon connection state, comparison browser/API and local regression. This is a working inventory, not completion of the required fresh independent acceptance audit.

| Priority | Issue | State / next action |
|---|---|---|
| P0 | Confirmed cross-tenant/data-loss/authentication bypass | No confirmed issue in executed boundary tests; do not infer absence of vulnerabilities from this scope |
| P1 | Hosted request timeouts and unexplained historical review latency | Investigating; local repeated authentication reads reduced5→2; request/SQL diagnostics implemented, not yet deployed |
| P1 | Hosted browser download verification | BLOCKED by cloud browser timeout; local Chromium download passed; retest hosted after diagnosing request path |
| P1 | Hosted responsive/manual accessibility acceptance | NOT TESTED; local viewport/axe checks do not substitute for hosted device coverage |
| P1 | Operational recovery/monitoring/retention | Synthetic restore passed; hosted isolated restore, alerts, retention enforcement and production rollback drill remain incomplete |
| P1 | Actual Render health-check configuration differs from Blueprint | Existing service reports empty HTTP health path (TCP probe); configure /health using supported authorized provider operation |
| P1 | Private repository integration and email-backed account workflows | Implementation/configuration incomplete; keep unavailable until real authorized provider tests succeed |
| P2 | Request and worker diagnostics / sensitive log minimization | Implemented locally: generated request references, template-only structured logs, parameter hiding, successful-query timing, generic errors |
| P2 | Report comparison usability | Deployed core comparison; spacing improvement and latest diagnostics release pending |
| P2 | Rule support documentation and controlled-fixture expansion | Existing Python/OpenAPI tests pass; remaining config/migration/dependency/JS-TS rules require scoped implementation and tests |
| P2 | Core New Scan and account/team/review workflows | Existing CI/local suites pass; repeat full hosted acceptance after final candidate |
| P3 | PDF, advanced graph, AI explanation, broader commercial billing | Incomplete; do not imply supported execution, private access or live payment readiness |

Do not enable public registration or public launch. Do not execute customer source. Preserve all existing application data and schema0002 review tables. Use only existing Free infrastructure unless explicitly approved otherwise.
