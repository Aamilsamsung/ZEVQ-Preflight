# Private beta development checkpoint — 28 October 2026

## Executive summary

**NOT READY FOR CONTROLLED PRIVATE BETA.** Provisional readiness **6/10**: the implemented static-analysis core, tenant boundaries and regression evidence are useful, but hosted browser/device coverage, recovery, retention/alerts and required integration workflows are not complete. This is an evidence-backed checkpoint, not the requested final independent acceptance audit or a security certification.

Live application commit: `b7701b2c6faffb5156796ed4693d1ed72ebe08f2`.
Render deploy: `dep-dbh3trafngtc73fb2oig`, confirmed live.
Database: PostgreSQL 16, existing Neon Free project, migration `0002` read back.
Architecture: existing Free Render web instance with separate supervised API/static worker processes; external Neon Free PostgreSQL; existing GitHub repository and CI. Public registration and commercial launch stay disabled. No paid services, customer-code execution or third-party AI transmission were enabled.

## Implemented changes and fixed issues

- Added stored-scan comparisons with exact finding-ID groups, changed evidence, original-report links, authenticated JSON download and coverage/source/engine warnings. Missing/duplicate/malformed legacy identifiers are unmatched, never guessed. Absence is not called a fix.
- Reduced repeated staging authentication plus membership reads from 5 SQL statements to 2 using a session/user join and request-local identity reuse. CSRF, server-side memberships and next-request revocation remain enforced.
- Added generated request references, route-template JSON logs, SQL/new-connection timing and generic error responses. Disabled default raw URL access logs in the supervised API and hid SQL bound parameters in exception representations.
- Added worker status/queue/elapsed diagnostics without source or remote error bodies. Discarded results are distinguished from published completion.
- Improved comparison panel spacing within the existing dark mint design. No unrelated redesign or fabricated statistics.

## Executed verification

| Requirement | Actual result | Status | Evidence | Remaining issue |
|---|---|---|---|---|
| Current Python suite | 145 passed, 2 PostgreSQL-only SQLite skips | PASS | Actions run `40745042435`, job `123016460581` | Starlette test-client deprecation warning remains |
| PostgreSQL/API boundaries | 54 passed, migration roundtrip passed | PASS | Same CI job | Not a general security certification |
| Browser regression | 37 workflow + 15 supplemental checks passed | PASS | CI Chromium, local API/worker | Local tests do not substitute for hosted device coverage |
| Synthetic restore | Row counts, login, report, review history and tenant isolation restored | PASS | Disposable PostgreSQL 16 CI drill | Hosted Neon restore remains NOT TESTED |
| Live commit/schema | Render live commit `b7701b2`; schema `0002` retained | PASS | Provider status and scoped Neon SELECT | Actual HTTP health-check setting still differs from Blueprint |
| Hosted comparison permissions | Eight controlled read checks passed after release | PASS | DIAGNOSTICS_VERIFICATION JSON | Cloud browser comparison download attempt timed out |
| Hosted review/scan retest | 13 checks passed: known scan, read-only/tenant restrictions, stale update, export, expiry/history | PASS | Latest DIAGNOSTICS_VERIFICATION JSON | End-to-end elapsed includes client/network/queue; browser submission remains blocked |
| Worker subprocess diagnostics | Matching completed-job event observed after final deployment | PASS | Provider log `a42b5696-be66-4458-b590-ecdd99a36fa5` | One empty-contract static job only |
| Request diagnostics | Live JSON logs show template routes, query counts, timings and generated IDs | PASS | Render log inspection | Alert delivery/log retention remain incomplete |
| Warm HTTP measurement | Same synthetic report, three report/save pairs per version | PASS | Before/after JSON | Too few samples for throughput or significant improvement claims |
| Actual hosted responsive browser | Certificate authority validation failed at login | BLOCKED | Hosted Chromium results JSON | Resolve runner trust without bypassing TLS, then rerun 390/768/1440 |
| Current cloud desktop pages | Dashboard/repositories/New Scan navigation observed | PASS | Live browser state | Complete remaining pages and critical actions |
| Current cloud scan journey | Browser transport disconnected during input step | BLOCKED | Browser transport error | Submission was not verified; recover browser and repeat |
| Full manual accessibility assessment | Not executed | NOT TESTED | Partial axe/local keyboard coverage only | Contrast, screen-reader and device checks remain |
| Full independent acceptance | Not complete | NOT TESTED | Working issue inventory | Re-audit mandatory requirements after blockers close |

The original `15504be` worker diagnostic implementation did not emit INFO in job children; hosted log inspection caught this. Follow-up `b7701b2` moves initialization before the job branch and adds an actual subprocess regression. Hosted verification confirmed scan `9bd447ad-f683-4580-91cc-f4e10deeb824` completed and emitted the matching redacted record in Render log `a42b5696-be66-4458-b590-ecdd99a36fa5`. This empty-contract job took 5.113 s end-to-end, with 4053.99 ms queue age at execution start and 213.72 ms worker duration. Queue age includes worker startup/connection time; this one sample does not establish production throughput.

## Performance before and after

| Measurement | Before | After | Scope |
|---|---:|---:|---|
| Authentication + membership SQL reads | 5 | 2 | Ten local SQLite component samples per version |
| Local auth component median |0.932ms|0.564ms|Excludes network/PostgreSQL/scan work; narrow profile |
| Warm hosted report median |0.280s|0.271s|Three sequential requests, same synthetic report |
| Warm hosted review-save median |0.325s|0.313s|Three sequential writes, same synthetic finding |
| Initial login client elapsed |8.057s|21.091s|Single first request per phase, not equivalent cold-start samples |

A separate same-input hosted scan/review retest completed in 14.635 s versus historical 13.422 s; its first review write took 8.282 s versus historical 7.95 s. Those end-to-end cases did not improve and remain a P1 investigation. The measurements above were executed at `15504be` before the worker-only logging follow-up. No material end-to-end speedup is claimed from three warm samples. A provisional free-tier evaluation target is warm report/review median under 2 s over at least 20 controlled sequential samples; the present three-sample run is insufficient to close that gate, and initial/cold requests require separate tracking. No SLA or guaranteed cold-start bound is offered. Latest warm report server spans were 24–26 ms with SQL 10–12 ms, versus client elapsed 258–291 ms. Matching server login was 1487.53 ms while the client measured 21.091 s, so the unexplained delay is largely outside that measured app span; it is not evidence of a 21-second database query. Network/proxy/connection behavior and free-tier cold starts require further controlled measurement. The first baseline login attempt timed out; one retry completed. No database index was added without a measured query justification.

## Security and recovery

No confirmed new cross-tenant bypass was found in executed checks. Authorization-cache, CSRF, next-request revocation, malformed input, concurrent review and sensitive-log/error tests passed. This limited scope does not establish absence of vulnerabilities. Only synthetic QA account/finding decisions were changed; customer data and existing review evidence were preserved.

No hosted snapshot, restore, branch swap, destructive cleanup or production rollback drill was performed. Neon project metadata confirms Free subscription and a 21,600-second history window. Existing snapshot list is empty. A normal branch copy alone would not constitute backup restoration. Keep the hosted recovery gate open; prepare an isolated, verified free method and obtain required authorization for any destructive restore operation before executing it. Never restore onto the live branch as a test.

## Remaining work and exact next actions

1. Recover the cloud browser connection and repeat the controlled OpenAPI New Scan journey from source through report/export/history. The last visible page was the API/OpenAPI tab in synthetic organization Independent QA 184337; submission was not confirmed.
2. Resolve the hosted Chromium runner certificate trust through an approved trusted environment, then execute scripts/hosted_browser_qa.cjs at all three widths. Do not disable certificate checks.
3. Configure the actual Render service HTTP health path to `/health` through an authorized provider operation; verify service state afterward. The connector currently exposes no update-service tool, and the existing Blueprint already has the desired path.
4. Complete safe isolated hosted recovery verification, retained-review consistency and an application rollback drill. Retain schema `0002` during code rollback.
5. Implement and test retention settings/cleanup safeguards and alerting; logs alone are not monitoring.
6. Prepare least-privilege private GitHub and verified email/recovery integrations, then request secure provider authorization only for the exact final configuration/testing steps. Keep unsupported flows unavailable meanwhile.
7. Expand supported analysis rules/documentation where deterministic fixtures justify them; complete the remaining P1 inventory and fresh acceptance table before any beta recommendation.

## Rollback and administrator guidance

Roll back application code to tested commit `9e78cde832e0d9213aae6450c5fb7d80f90ff6f4`, retaining additive schema `0002` and all scan/review data. Do not downgrade the live schema. Verify HTTPS, login, tenant-scoped reports, queue processing and review history after rollback. This runbook was not executed as a hosted rollback drill.

Use the existing OPERATIONS.md trusted operator flow for provisioned access and identity-verified recovery. Never paste passwords into chat or commit secret files. Diagnostics can be searched by generated X-Request-ID in Render logs. This checkpoint does not authorize public signup, payment activation or launch.
