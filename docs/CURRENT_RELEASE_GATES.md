# Current release gates — 28 October 2026

This is the current tracker; earlier audit reports remain historical evidence. The product remains restricted evaluation, not an approved public SaaS launch. Free Render/Neon resources are in use. Railway is excluded.

| Gate | State | Evidence / next requirement |
|---|---|---|
| Persistent database, migrations and scoped APIs | PASS | CI PostgreSQL migration cycles and API isolation tests; hosted schema0002 |
| Provisioned sessions, password change, operator recovery and team roles | PASS | Account-control CI and hosted synthetic tests; no automated email recovery |
| Public repository / ZIP / OpenAPI static analysis | PASS | Supported-rule fixtures, bounded fetch/upload tests and recorded live QA; unsupported cases remain disclosed |
| Finding reviews/history/suppression | PASS | Commit576fd92; 13 hosted checks plus live browser persistence/history |
| Scan comparison | BLOCKED | Commit9e78cde passed139 Python/49 PG/52 browser checks; live finding/evidence verified; cloud download timed out and hosted permission run has partial evidence |
| Runtime simulation | BLOCKED | No approved execution sandbox; execution stays disabled |
| Private GitHub, OAuth, PR/webhook/scheduled integration | FAIL | Not implemented/configured |
| Email verification/invitations/reset and MFA | FAIL | Provisioned-account evaluation only |
| Billing and entitlements | FAIL | No live payments; provider integration incomplete |
| PDF reports / full impact graph / JS-TS analysis | FAIL | Remaining implementation |
| Local responsive browser regression | PASS | Automated 390/768/1440 checks; not a full mobile-device assessment |
| Hosted mobile and complete accessibility assessment | NOT TESTED | Requires separate manual/device coverage; axe incomplete rules are not a WCAG certification |
| Synthetic PostgreSQL restore | PASS | CI row counts, auth, report, review history, two-user isolation |
| Hosted Neon restore / production rollback drill | NOT TESTED | Runbook available; hosted drill not executed |
| Hosting readiness configuration | FAIL | Free cold-start observed; actual Render service still uses TCP probe despite /health in Blueprint |
| Monitoring/alerts/retention and load validation | FAIL | Request/SQL/connection logs and worker job events verified atb7701b2; alerting, retention and load validation incomplete |
| Terms/privacy professional review | NOT TESTED | Draft informational pages only |
| Public registration / launch | BLOCKED | Explicit owner launch approval required after release gates pass |

No PASS here establishes security certification or guaranteed failure prediction. Scores describe rule-based review priority. No customer source is sent to an external AI provider or executed.
