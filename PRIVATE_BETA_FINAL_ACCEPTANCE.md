# ZEVQ Preflight — final private-beta acceptance

Assessment: 29 October 2026 (Asia/Calcutta; provider timestamps UTC 28 October). **NOT READY FOR CONTROLLED PRIVATE BETA**. Readiness: **6/10**, a qualitative assessment, not a completion percentage or security certification.

Staging: https://zevq-preflight-staging.onrender.com. Repository: https://github.com/Aamilsamsung/ZEVQ-Preflight.

Application commit **5e0e211fe10045d6fbb4ee8c6b3c0b31cd706c70**, Render deployment **dep-dbh4jk6c6qcc73cihja0**, confirmed live through the provider API. Verification-only changes are in draft PR2, on `audit/acceptance-verification-20261029`; they do not change application, static assets, migrations or requirements relative to this deployed commit. Draft PR1 remains unmerged. Public launch is not approved.

## Delivered changes

Existing FastAPI application and visual theme retained. Added owner-controlled retention policy, expiring dry runs, explicit confirmation, scoped audit history and concurrency-safe preservation of reviewed scans. Cleanup is manual and disabled by default. Added durable-data-derived in-app failure, queue-delay and stale-job alerts with per-member acknowledgements. Improved bounded GitHub error diagnostics without leaking provider bodies. Fixed keyboard access to scrolling tables and the empty retention preview rendering `null`. No customer code execution or AI transmission was enabled.

## Executed verification

| Feature | Expected | Observed / evidence | State | Severity / required action |
|---|---|---|---|---|
| Python regression | Existing and new rules pass | CI40752162231 and verification CI40753599019:164 passed,3 PostgreSQL-only skips in general suite | PASS | None; skips covered by PostgreSQL suite |
| PostgreSQL boundaries | Tenant, role, CSRF and concurrent review protection |65 passed; migrations up/down/up in disposable CI database | PASS | No hosted downgrade performed |
| Browser regression | Core interactions remain working |37 main +19 supplemental local browser checks passed | PASS | Coverage is not every possible interaction |
| Hosted workspace | Refresh/session, navigation, reviews, keyboard and errors |62 checks passed at390/768/1440px;27 axe states; no violations | PASS | Manual assistive-technology review remains separate |
| Hosted informational pages |200, heading, no overflow, no axe violations |12 pages ×3 widths plus custom404:37 passed | PASS | Read-only coverage; not every form/link clicked |
| OpenAPI New Scan | Removed endpoint yields evidence |Scan f1f319a6-980d-4361-bf24-5f7eef62dd46:one finding; JSON/CSV parsed; refresh/history passed | PASS | Supported contract rules only |
| Public GitHub New Scan | Same immutable revisions have no breaking findings |Scan38238088-26a4-4673-95d1-931a11995f85:zero findings; JSON/CSV and history passed | PASS | Authorized project repository only |
| ZIP New Scan | Removed Python function detected |Scan b2044e98-75e5-41ba-be29-61037388ce1c:one finding; JSON/CSV and history passed | PASS | Static inspection only |
| Failure handling | Honest failure and in-app notification |Actual invalid-ref failure and persistent acknowledgement observed; later GitHub403 rate limit shown without retry | PASS | Final hosted422 diagnostic branch BLOCKED by provider quota; deterministic fixture passes |
| Retention | Disabled default; preview before deletion |Synthetic org7-day preview:zero eligible; policy restored to disabled; live SELECT enabled=0, applied=0 | PASS | No live deletion attempted; destructive behavior tested in isolated CI |
| Mobile Audit accessibility defect | Table receives keyboard focus |Original serious axe failure fixed; regression and hosted rerun pass | PASS | Preserve focusable shared table wrapper |
| Full WCAG2.2AA assessment | Manual contrast, screen-reader/device assessment |Axe incomplete rules include color-contrast, aria-prohibited-attr, link-in-text-block | NOT TESTED | Medium; complete manual review; no WCAG certification claimed |
| Known dependency advisories | No known vulnerable locked dependencies |pip-audit:34 dependencies,zero known vulnerabilities,zero skipped | PASS | Limited to audit database and dependency scope |
| CI backup/recovery | Restored data and access boundaries usable |Actual pg_dump/pg_restore; session, report, reviews/history, retention and tenant checks pass; restored queued static job completes | PASS | Synthetic disposable PostgreSQL only |
| Previous-source compatibility | Fallback reads additive schema safely |Exact9e78cde832e0d9213aae6450c5fb7d80f90ff6f4 source passes restored session/report/history/isolation at schema0003 | PASS | Does not establish previous-worker or hosted rollback success |
| Hosted Neon recovery / actual service rollback | Recovery rehearsed against isolated hosted target |Not performed; no live database restore or destructive action | NOT TESTED | High; controlled hosted recovery drill required |
| Render HTTP health check | Provider probes /health |Provider reports empty healthCheckPath, despite Blueprint setting | BLOCKED | High; exact owner action below |
| External availability/email alerts | Operator receives service outage notification |In-app alerts work; external delivery not configured | BLOCKED | High; configure approved free alert delivery and verify receipt |
| Email recovery / verification | Safe customer self-service |Provisioned-account/operator recovery only; email delivery disabled | FAIL | High; implement and verify delivery, or explicitly approve narrower evaluation scope |
| Private GitHub / OAuth | Authorized private repository integration |Unavailable, visibly disabled | FAIL | Required roadmap work; no unsupported claim |
| Controlled idle cold-start / resource load | Measured under defined idle/load conditions |Not measured in controlled conditions | NOT TESTED | Medium; bounded measurement, no denial-of-service test |
| Billing / sandbox / public signup | Disabled until approved and ready |Remain disabled; no paid resources purchased | PASS | These are unavailable features, not completed integrations |
| Legal review | Reviewed terms/privacy |Draft pages exist; professional review unverified | NOT TESTED | Complete before commercial release |

Counts are separate suites, not unique requirements: **389 automated assertions/checks passed** (164 Python +65 PostgreSQL +56 local browser +62 hosted workspace +37 hosted public +3 hosted scan journeys +2 recovery/compatibility script runs);3 skipped in the general Python run. Recovery scripts contain multiple assertions counted here as one run each. No current failing automated checks in those runs. Historical mobile accessibility failure was fixed and rerun. Blocked/not-tested release gates are not counted as passes. Supplemental manual observations are not inflated into this total. See `docs/acceptance-2026-10-29/` for sanitized hosted evidence; CI run IDs identify remote logs.

## Measured performance

Twenty sequential warm report/save pairs per phase, using synthetic data; this is not a concurrency benchmark. Baseline commit b7701b2:report median281.5ms,p95452ms,max715ms; review median312.5ms,p95347ms,max424ms. Current deployed commit:report median265.5ms,p95286ms,max295ms; review median301.5ms,p95335ms,max341ms. The provisional warm median under2seconds target is met. Small phase differences are not evidence of a causal optimization.

Current login8.686seconds:client trace showed7.027seconds waiting for the proxy CONNECT response,3.076ms TLS phase and1.652seconds waiting for the target response headers. This identifies the dominant delay in this measured test path; it does not prove all user latency is proxy-related. No TLS checks were bypassed:Chromium trusted the existing system-managed root CA in the ephemeral runner NSS store, with no ignore-certificate-errors flag.

Complete hosted UI journeys including setup, exports and history took11.264seconds OpenAPI,11.577seconds GitHub and12.142seconds ZIP. These are not isolated scanner execution times. Hosted database query plans, memory ceilings and idle cold-start latency have not been comprehensively measured.

## Architecture, operations and remaining scope

Existing single Free Render service runs FastAPI and supervised static scan worker; durable PostgreSQL job state resides in existing Free Neon PostgreSQL16. Live migration0003 and runtime grants were verified. No dedicated paid worker, new paid plan or Railway dependency was introduced. Free-tier resource/cold-start constraints remain. This is not an SLA or a guaranteed zero bill; no new charge was authorized or incurred by these changes.

The scanner uses supported reproducible rules and evidence. It does not predict every failure, execute customer source, provide full JS/TS analysis, or produce guaranteed failure probabilities. PDF reports, complete impact graph, private-source integration, email invitations/recovery, MFA, subscriptions/payment provider, scheduling/PR checks, broader simulation and enterprise administration remain incomplete. Public report access is not substituted for tenant authorization. No customer/private source was used in these controlled scans.

Administrator setup remains provisioned closed-staging accounts using host secret settings and the documented interactive operator recovery procedure in `docs/OPERATIONS.md`. Never send passwords, database URLs or API keys in chat. Existing bootstrap variables do not reset existing passwords. User workflow and limitations are documented at `/docs` and in `docs/RETENTION_AND_ALERTS.md`.

Rollback:do not downgrade or restore over the live database. Preserve a verified backup; validate fallback source9e78cde against a separate restored database first. Additive schema0003 compatibility passed in CI. An authorized operator can select a previously successful Render deployment only after that rehearsal and health verification. A real hosted rollback has not been executed.

## Exact remaining acceptance actions

1. In https://dashboard.render.com/web/srv-dbgr4v0n74is73d798e0 → Settings → Health Checks → Edit,set `/health`,Save. Re-read the provider configuration and verify an application-health failure is detected. The connected Render tools expose no service-setting update operation; a Blueprint file alone does not change this existing service.
2. Rehearse hosted recovery on an isolated approved target, verify restored sessions/data/tenant boundaries and static worker recovery,then demonstrate service rollback without overwriting live data.
3. Configure and test an approved free external availability/alert channel. In-app alerts cannot notify an operator when the whole application is unavailable.
4. Complete manual accessibility checks and controlled cold-start observation. Finish email recovery and private repository integration,or obtain explicit approval for a reduced provisioned-account/public-source-only evaluation scope. No such scope approval is assumed.
5. Keep public registration,payments and customer-code execution disabled. Request launch approval only after the applicable gates pass.

**NOT READY FOR CONTROLLED PRIVATE BETA**
