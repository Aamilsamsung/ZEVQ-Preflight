# Current launch blockers

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


Completed evidence is indexed in FINAL_PRODUCTION_QA_REPORT.md. Do not repeat completed suites without relevant changes. Current independent improvements include authenticated-browser preparation, fresh dependency audit and rollback-startup remediation. Continue only newly unblocked acceptance after owner setup and concurrency checks.
