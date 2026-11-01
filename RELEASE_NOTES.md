# Release notes — protected staging candidate

- Live URL: https://zevq-preflight-staging.onrender.com
- Deployed application: `e612f03dda7cd10d139ec4b95472ce978d5bf14c`
- Render deployment: `dep-dbj34r7b9u1s73cu1qqg` — live
- Render service: `srv-dbgr4v0n74is73d798e0`, Free, automatic deployment off
- Configured release branch: `implementation/secure-preflight`
- Active development branch: `implementation/public-onboarding-20261029`
- Neon project: `dawn-bonus-77001287`; live migration: `0006`
- Report commit: the Git commit containing this file.

## Deployed functionality

Provisioned login and revocable sessions; tenant-scoped organizations and roles; static public GitHub/ZIP/OpenAPI scans; evidence, findings, reviews/history, comparisons and JSON/CSV exports. Migration 0006 adds gated mailbox-first onboarding support, account events and nullable scan attribution without resetting existing accounts.

Public onboarding/email and private GitHub implementations remain gated pending real integration acceptance. Billing and execution of customer programs remain disabled. GitHub App/OAuth and email invitations are not offered as working features.

## New development/release tooling

- Secure authenticated-browser runner with a dedicated Actions-secret fixture, source guards, organization selection and sanitized artifacts.
- Fresh locked-manifest dependency advisory evidence.
- Allowlisted hosted recovery-application runner and original-row preservation safeguards.
- Explicit synthetic notification transport drill with issue-index-lag correction.
- Previous-application rollback bundle preserving current migration history; tested on SQLite and PostgreSQL16.
- Complete recovery, monitoring, operations and owner setup documents.

These additions have not changed the live application commit. Tooling readiness is not public-launch acceptance.

| Area | Executed evidence | Limit |
|---|---|---|
| Core hosted APIs | 55 passed | Provisioned synthetic identities; not public email onboarding |
| Anonymous hosted browser | 19 passed, 0 failed/blocked; run 41230780595 | Five anonymous pages at 390/768/1440px; not authenticated workspace |
| Current full CI | 233 SQLite passed, 126 PostgreSQL passed, 5 skipped; run 41270626594 | Skips are not passes |
| Dependency advisory review | pip-audit 2.10.1; 35 exact pins; 0 known vulnerabilities, 0 skipped | PyPI advisories and pinned manifest; not proof of absence of vulnerabilities or a new transitive resolution |
| QA fixture safety | 8 local validation/redaction checks passed | Authenticated hosted runner still awaits a secret |
| Recovery runner safety | 7 local tests passed | Actual isolated hosted application run awaits its secret |
| Notification drill | 4 safety checks; actual issue 6, recovery comment and closure; run 41231200409 | Inbox receipt and recurring scheduling unverified |
| Rollback startup | 2 local tests; dedicated run 41270626650: 2 SQLite and 2 PostgreSQL passed | Prepared source bundle; not an actual hosted rollback |

## Release verdict

**NOT READY — BLOCKERS REMAIN.** Final public launch requires complete technical evidence and separate explicit owner authorization.
