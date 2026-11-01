# Production QA — NOT READY — BLOCKERS REMAIN

- Live URL: https://zevq-preflight-staging.onrender.com
- Deployed application: `e612f03dda7cd10d139ec4b95472ce978d5bf14c`
- Render deployment: `dep-dbj34r7b9u1s73cu1qqg` — live
- Render service: `srv-dbgr4v0n74is73d798e0`, Free, automatic deployment off
- Configured release branch: `implementation/secure-preflight`
- Active development branch: `implementation/public-onboarding-20261029`
- Neon project: `dawn-bonus-77001287`; live migration: `0006`
- Report commit: the Git commit containing this file.

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

| Remaining gate | Required action/evidence |
|---|---|
| Render HTTP health check | Save `/health` in existing service settings; independently read back provider configuration |
| Real email | Configure approved TLS SMTP sender in Render; verify received verification/resend/reset messages and complete protected user journeys |
| Private GitHub | Owner authorizes one restricted private fixture through Preflight; verify revisions, findings, isolation, disconnect and provider revocation |
| Notification receipt/scheduling | Configure GitHub subscription/email preferences; one fresh receipt drill; review default-branch workflow placement and opt-in/token configuration |
| Authenticated hosted browser | Configure `PREFLIGHT_HOSTED_BROWSER_FIXTURE` as an Actions secret; trigger a fresh guarded browser run |
| Isolated hosted recovery | Configure `PREFLIGHT_RECOVERY_DATABASE_URL` for the named snapshot as an Actions secret; trigger a fresh guarded run |
| Legal/support | Explicit owner review of draft, retention/support decisions and factual amendments |
| Public launch | All technical gates pass, followed by a separate explicit owner launch authorization |


The rollback startup gap was reproduced and a prepared source-bundle remedy passed dedicated SQLite/PostgreSQL CI. An old Render artifact is not a proven rollback path. Authenticated browser and actual hosted restored-application runners are prepared but unexecuted pending secure prerequisites. No visual/UI completion or public onboarding claim is inferred from unit tests, anonymous pages or provisioned API identities.
