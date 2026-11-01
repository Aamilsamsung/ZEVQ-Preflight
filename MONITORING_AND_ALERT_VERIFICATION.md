# Monitoring and alert verification

- Live URL: https://zevq-preflight-staging.onrender.com
- Deployed application: `e612f03dda7cd10d139ec4b95472ce978d5bf14c`
- Render deployment: `dep-dbj34r7b9u1s73cu1qqg` — live
- Render service: `srv-dbgr4v0n74is73d798e0`, Free, automatic deployment off
- Configured release branch: `implementation/secure-preflight`
- Active development branch: `implementation/public-onboarding-20261029`
- Neon project: `dawn-bonus-77001287`; live migration: `0006`
- Report commit: the Git commit containing this file.

| Signal/channel | Verified | Not established |
|---|---|---|
| Application/database health endpoint | Actual hosted health returned healthy/database reachable | Provider HTTP health path remains blank |
| Aggregate operational endpoint | Implemented with protected aggregate booleans; deterministic tests passed | Matching monitor secrets and actual worker/queue incident acceptance |
| GitHub incident/recovery transport | Corrected run 41231200409 created issue 6, posted recovery comment, closed it after a healthy probe | Authorized inbox receipt |
| Deduplication/probe behavior | Existing 8 deterministic monitor checks passed | Independently scheduled live incident/recovery cycles |
| Recurring availability | Workflow prepared | Default-branch placement and opt-in configuration |
| Idle worker/full API error rate | Limitations documented | No complete idle heartbeat or every-request error-rate signal |

The initial synthetic drill failed because the immediately created issue was absent from the list index. It was closed as incomplete (issue 5), not counted as success. The corrected drill reads its returned issue ID directly. It checks the source head before each issue mutation and refuses blind repeat attempts. No real service outage was induced.

Connected inbox searches found no matching drill notification at observation. Creating an issue or posting a recovery comment does not prove email/push receipt. Configure the repository subscription and account email notification preferences before one new deliberate drill. Do not keep sending unchanged tests.

The existing availability workflow is not active on the default branch. Preserve the old main branch; reconcile reviewed workflow/script changes separately. The optional operational endpoint requires a matching privately generated `PREFLIGHT_MONITOR_TOKEN` in Render and Actions secrets. Health-only monitoring must not be sold as full worker/error monitoring.

See OWNER_SETUP_ACTIONS.md and OPERATIONS_RUNBOOK.md. No 24/7 availability or alert-delivery SLA is claimed on free infrastructure.
