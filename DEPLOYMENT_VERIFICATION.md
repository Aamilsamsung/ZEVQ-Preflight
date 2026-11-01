# Staging deployment verification

- Live URL: https://zevq-preflight-staging.onrender.com
- Deployed application: `e612f03dda7cd10d139ec4b95472ce978d5bf14c`
- Render deployment: `dep-dbj34r7b9u1s73cu1qqg` — live
- Render service: `srv-dbgr4v0n74is73d798e0`, Free, automatic deployment off
- Configured release branch: `implementation/secure-preflight`
- Active development branch: `implementation/public-onboarding-20261029`
- Neon project: `dawn-bonus-77001287`; live migration: `0006`
- Report commit: the Git commit containing this file.


The application deployment finished at 2026-10-31T18:26:03Z. It used a reviewed guarded fast-forward of the configured release branch and applied additive migration 0006. The pre-QA baseline was preserved; later synthetic fixture additions were documented separately. No new production deployment, key rotation, password reset, destructive recovery or paid upgrade occurred in this increment.

The endpoint returned healthy/database reachable previously. The provider health path remains an owner configuration gate. Test and operational tooling commits do not change the live application commit or require redeploying it.

Rollback must use reviewed prepared source retaining current migration history; the old artifact cannot resolve revision 0006. See ROLLBACK_STARTUP_VERIFICATION.md and OPERATIONS_RUNBOOK.md. Actual hosted rollback has not been attempted.

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
