# ZEVQ Preflight independent live QA and security audit

28 October 2026 · ZEVQ Labs · restricted staging

**Verdict: NOT READY FOR PRIVATE BETA. Readiness: 6/10.** This is an engineering judgment, not a certification or a measured failure probability. The supported static-analysis workflow demonstrably works, but the confirmation UI, dialog accessibility, evidence pointers and incomplete release-boundary verification prevent a clean recommendation. No critical/high exploit was demonstrated in the bounded checks; that does not establish their absence.

The inspected and deployed application commit is **`fd8e122b0a6105cc94adc43fecca4c816618b1df`**. Render deploy **`dep-dbgstehsrm7s73enn6ug`** was verified live. Local source HEAD and GitHub commit match. Audit scripts/tests/report are subsequent audit-only additions on a separate branch; they do not change that deployed application. Prior completion reports were not used as proof.

## Execution totals

| Evidence group | Executed | Passed | Failed / open | Skipped |
| --- | ---: | ---: | ---: | ---: |
| Expanded Python suite (106 collected) | 105 | 103 | 2 expected failures | 1 PostgreSQL-only local skip |
| Existing real-browser local workflow suite | 37 | 37 | 0 | 0 |
| Fresh live API/security assertions | 43 | 42 | 1 | 0 |
| Recorded live cloud-browser checks | 27 | 24 | 3 | 0 |
| Supplemental local UI/accessibility checks | 8 | 6 | 2 | 0 |
| **Total** | **220** | **212** | **8** | **1** |

The eight non-passing executions include repeated reproductions of the same defects; they are not eight unique vulnerabilities. Two strict pytest `xfail` tests reproduce open defects and are explicitly counted as failures here, never as passes. Six supplemental passes mean zero violations under the selected supported axe rules; incomplete contrast/other rules are not passes. CI’s separate 19 PostgreSQL checks and its repeated102/37 checks are not added to these totals. Database profiling and dependency auditing are measurements, also excluded from test totals. BLOCKED/NOT TESTED items below were not executed and are excluded.

Six API scans and two live browser scans used synthetic inputs or the owner's authorized public repository. A labeled QA organization was created and retained; no accounts/organizations were deleted, no real users invited, no production deployments blocked, and no paid services enabled. One browser contract scan was recorded in the original organization before the synthetic organization became available; its source contains only the synthetic `/audit-orders` contract.

## Feature matrix

| Feature | Expected behavior | Actual observed behavior | State | Evidence | Severity | Required fix |
| --- | --- | --- | --- | --- | --- | --- |
| Deployed version | Live build equals inspected source | Render live deploy dep-dbgstehsrm7s73enn6ug points to fd8e122…; local HEAD and GitHub commit match | PASS | GitHub + Render API | — | None |
| Secure browser sign-in | User authenticates without exposing credentials | Secure browserAuth handoff succeeded; authenticated dashboard visible | PASS | Live cloud Chrome | — | None |
| Refresh persistence | Refresh preserves account session | Workspace and navigation remained accessible after reload | PASS | live-browser-results.json | — | None |
| Primary navigation | Workspace routes open real pages | Projects, Reports, Organizations, Audit log, Settings, Dashboard rendered headings | PASS | 6 live browser transitions | — | None |
| Public navigation | All existing information links work | Landing, docs, features, how-it-works, security, contact, FAQ, use cases, pricing, privacy, terms and cookies opened | PASS | Live browser, signed-in staging session | — | None |
| Signed-in landing CTA | Open existing workspace directly | Open your workspace sends an authenticated user to /login | FAIL | Live browser + publicShell state handling | Low | Load session state on public pages; use /app when authenticated |
| New Scan source/configuration | Tabs, preview, Back preserve inputs | OpenAPI and ZIP tabs worked; preview refreshed; Back preserved contracts | PASS | Live browser contract and ZIP workflows | — | None |
| Review summary | Display selected input rows for confirmation | Four [object HTMLDivElement] strings, zero summary .key-value elements | FAIL | Live screenshot; supplemental regression | Medium | Spread mapped nodes into review.replaceChildren |
| OpenAPI breaking change | Removed endpoint produces reproducible finding | GET /orders and browser /audit-orders removals detected; rule OAS.ENDPOINT_REMOVED, high confidence | PASS | 6505af7b… and 66762936… | — | None |
| Safe contract | Unchanged contract produces no findings | 0 findings for identical OpenAPI specs | PASS | 3b45cabd… | — | None |
| Python ZIP changes | Detect removed function and required argument | Removed removed_api high; public_api signature change medium | PASS | d33bd4af… | — | Consider more precise severity for confirmed required-argument changes |
| Safe Python | No unjustified critical/high warning | Identical Python archives had no high/critical findings; browser safe.py had zero findings | PASS | c0fdc15b… and f0a053b1… | — | None |
| Public GitHub branches | Fetch authorized repository and compare revisions | Own repository main → main completed; branches are text refs rather than branch-picker discovery | PASS | 8ebf41f8… | — | Add branch discovery later; immutable SHAs advised |
| Job lifecycle | Persistent queued/running/final states | All six API jobs observed queued → running → completed/failed | PASS | live-api-results.json scans | — | None |
| Failure handling | Invalid ref becomes failed, not simulated success | GitHub HTTP404 failure recorded with safe error message | PASS | d68814fe… | — | None |
| Evidence location | Evidence pointer resolves to source OpenAPI node | /paths//orders/get does not resolve as RFC6901 JSON Pointer | FAIL | Expected-failure regression AUDIT-05 | Low | Escape path segments using ~1 and ~0 |
| Report downloads | Authorized JSON/CSV downloadable | Both API formats succeeded; actual browser JSON download completed | PASS | report export checks and browser download | — | None |
| History and dashboard | Show stored results | Six synthetic API jobs appeared; aggregate scan count matched at check time | PASS | Controlled organization f95c92d4… | — | None |
| Anonymous protection | Private API/reports deny unauthenticated requests | HTTP401; /app redirects303 to /login; registration403 | PASS | Live API checks | — | None |
| CSRF and Origin | Reject unauthenticated mutation context | Missing CSRF and foreign Origin rejected403 | PASS | Live API checks | — | None |
| Session cookie/revocation | Secure cookie and server-side logout | Secure, HttpOnly, SameSite Strict; replay after logout401 | PASS | Live API + source inspection | — | None |
| Tenant/resource scope | Deny unrelated organization/resource IDs | Five random nonmember-org routes404; own scan under different own organization404 | PASS | Live scoped-ID checks | — | None |
| Two-user live tenant/RBAC matrix | Different users/roles cannot cross tenants | Only one provisioned live principal available; local tests cover isolation/viewer denial | BLOCKED | No second test account | High verification priority | Provision isolated second-user/viewer accounts and repeat hosted matrix |
| Upload/input validation | Reject malformed/traversal inputs | ZIP ../ and drive paths422; malformed ZIP422; invalid contracts and unsafe repo inputs422 | PASS | Bounded live API tests | — | None |
| Rate limiting | Bound repeated failed sign-in | 10 synthetic unknown-account attempts401; attempt11 returned429 with Retry-After900 | PASS | 11 sequential live requests; no real-account lockout | — | None |
| Secret exposure checks | Do not serve operator secrets/source | Known operator secrets absent from JS/CSS; .env/.git/config/traversal requests404; account export omitted hash fields | PASS | Bounded authenticated API checks | — | Not a comprehensive secret-history scan |
| Security headers | Apply security headers on errors too | Authenticated page has CSP/HSTS/frame/nosniff/referrer headers; early anonymous401 omits them | FAIL | Live API + AUDIT-02 regression | Low | Apply common headers to every middleware return |
| Destructive dialog cancel | Cancel performs no deletion | Delete-account confirmation opened and cancelled; no delete request submitted | PASS | Live browser | — | None |
| Dialog accessibility | Dialog has programmatic accessible name | No aria-label/aria-labelledby; named-dialog lookup fails | FAIL | Live DOM and supplemental browser regression | Medium | Associate title/description with native dialog |
| Desktop design consistency | Use approved dark mint theme | Observed matching sidebar, dark cards, mint actions, evidence panels and typography | PASS | Live browser and screenshots | — | Review page defect still needs fixing |
| Responsive layouts | No overflow at mobile/tablet/desktop | Local real browser suite checks390/768/1440px on public/workspace pages | PASS | Fresh 37-check local regression run | — | None |
| Hosted mobile/touch browsers | Validate actual hosted page at small viewports | Cloud browser did not expose viewport resizing; no real mobile device used | BLOCKED | Local responsive checks do not replace hosted mobile QA | Medium verification priority | Repeat hosted mobile Safari/Chrome and touch testing |
| WCAG AA completeness | Verify contrast, keyboard and assistive technology | Six local axe states report0 supported violations; color-contrast and some other rules incomplete; unnamed dialog confirmed | NOT TESTED | Supplemental axe evidence lists incomplete rules | Medium | Manual contrast and screen-reader assessment; fix dialog |
| Console errors | No application errors during normal flow | No target-domain warn/error entries in live browser; extension metadata errors excluded; local37 checks zero errors | PASS | Live dev.logs filter and browser-regression-results.json | — | None |
| Network completeness | Capture all failed requests/HAR | Expected401/403/404/422/429 tested; full browser HAR unavailable | NOT TESTED | No complete live browser network trace | — | Capture HAR/DevTools network in a follow-up |
| Dependencies | Audit pinned Python packages | Fresh pip-audit:33 dependencies,0 known vulnerabilities | PASS | dependency-audit.json | — | Not a security certification or JS supply-chain audit |
| Database/query profile | Measure query cost and inspect isolation | Instrumented local staging dashboard:7 SELECTs; pool2 + overflow2 in source | PASS | query-profile.json; hosted PostgreSQL EXPLAIN not run | — | Reduce duplicate auth lookups; verify hosted plans separately |
| PostgreSQL migrations | Upgrade/down/up and restricted runtime checks pass | GitHub job122763014291 for deployed SHA:19 checks passed, migration step successful | PASS | Independently fetched CI metadata and logs | — | Not a backup/restore exercise |
| Backup/restore/recovery | Restore a backup and recover operation | No restore drill executed; account recovery delivery disabled | NOT TESTED | No destructive/operational drill performed | High release blocker | Complete restore drill and documented operator account-recovery procedure |
| Runtime isolation | Never execute customer code in API | Static worker path inspected; browser and reports explicitly say no runtime execution | PASS | app.worker/app.serve inspection and live reports | — | Runtime execution remains disabled; sandbox capability not tested |
| Cancellation/retry/worker death | Eligible jobs cancel/recover under failure | Existing local worker tests pass; hosted cancel/restart tests not executed | NOT TESTED | Avoided disruption to shared staging | Medium | Exercise hosted eligible cancellation and controlled worker recovery |
| Every remaining button/form | Validate all state-changing functions | Deletion, membership changes, logout-all, private OAuth, emails, billing and exhaustive negative forms not submitted | NOT TESTED | Scope constrained to non-destructive authorized checks | — | Provision disposable accounts and complete remaining matrix |

## Confirmed defects

1. **AUDIT-01 · Medium · Review summary is broken.** Source → Configuration → Review displays `[object HTMLDivElement]` four times. In `static/app.js`, native `review.replaceChildren` receives `inputSummary().map(...)` as one array argument. Spread the generated nodes. Live screenshot `zevq-audit-review-defect.jpg` and supplemental test both reproduce it. The scan can still submit, so this is not a scanner failure.
2. **AUDIT-02 · Low · Early responses omit security headers.** Staging authentication and some mutation rejections return before common header application. Anonymous401 was verified missing CSP, X-Frame-Options, nosniff, HSTS and Referrer-Policy. Apply common headers consistently. This did not bypass authentication.
3. **AUDIT-03 · Medium · Confirmation dialog has no accessible name.** `dialog` has no aria-label/aria-labelledby; its heading/description are unassociated. Add aria-labelledby="confirm-title" and aria-describedby="confirm-text", then retest keyboard/screen-reader behavior.
4. **AUDIT-04 · Low · Signed-in landing CTA opens login.** Public rendering does not load the existing session into client state, so an authenticated user clicking Open your workspace sees login. Direct /app still works. Resolve session state and route appropriately.
5. **AUDIT-05 · Low · OpenAPI evidence pointer is not resolvable.** `/paths//orders/get` is not the correct RFC6901 pointer for a `/orders` key; it should encode the slash as `~1`. Strict regression reproduces the resolution failure. Findings themselves were otherwise correct.

The Python audit initially expected two high-severity findings. Inspection showed the engine intentionally assigns medium to generic signature changes. That overly strict test oracle was corrected against the saved result: both requested changes were detected. The report does not call that severity policy a failed detection.

## Performance measurements

These are small sequential samples over this environment’s network path, not a load/capacity benchmark or service SLA.

| Measurement | Observed | Limitations |
| --- | --- | --- |
| First /login document request | 7,998.6 ms | HTTP document only; includes TLS/proxy/network; not browser LCP |
| Subsequent /login samples | 471.7 ms;256.7 ms | Three total document samples; no deliberate cold-start test |
| Live navigation interactions | 388–1,401 ms | Six navigation clicks to visible headings; includes automation overhead |
| Readiness API | median271.9 ms; max276.8 ms | n=3 |
| Dashboard API | median280.0 ms; max286.3 ms | n=4 including initial assertion |
| History API | median283.2 ms; max505.3 ms | n=4 |
| OpenAPI removal job | 6,060.9 ms wall /122.29 ms engine | Polling/queue/network included in wall |
| Unchanged OpenAPI job | 5,069.6 ms /202.44 ms | wall /engine |
| Python breaking-change job | 5,296.0 ms /219.32 ms | wall /engine |
| Unchanged Python job | 11,517.5 ms /122.17 ms | wall /engine; queue/network dominate |
| GitHub main → main job | 7,679.4 ms /2,497.06 ms | wall /engine includes source download |
| Invalid ref failed job | 6,610.9 ms wall | No successful engine duration |
| Render current-instance samples | 136.8–139.3 MiB /512 MiB limit | Provider samples through10:42 UTC; before controlled scan burst |
| Render CPU sample | 0.0019607467 CPU /0.15 CPU limit | Not a peak-load measurement |
| Local dashboard SQL | 7 SELECT statements per request | SQLite staging middleware instrumentation; not hosted query timings |

Source review found bounded archive size8 MB,400 analyzed files,300 KB per file; worker timeout120s, analysis timeout90s, CPU limit60s and address-space limit768 MiB. The host’s512 MiB memory cap is lower than that worker address-space allowance and is shared with API/supervisor processes. No OOM or stress test was run. PostgreSQL pool size2 plus overflow2 applies per process, not globally. Consider reducing repeated authentication queries (seven total SELECTs in an empty dashboard request) and align worker memory limits with the host budget. No capacity guarantee follows from the observed idle memory samples.

## Browser and UI scope

Live cloud Chrome verified sign-in, refresh, all primary navigation pages, existing public pages, source tabs, preview refresh, Back, review, actual OpenAPI and ZIP submissions, evidence expansion, actual JSON download, organization switching, and destructive-modal cancellation. The actual safe ZIP report showed0 findings and explicitly said no runtime tests executed. No target-domain warning/error entries were returned by live console inspection; browser-extension metadata errors were present and excluded from application findings. A full HAR capture was unavailable.

The fresh local real-browser suite checks login, scans, reports, history, team/settings, errors, keyboard skip navigation and responsive layouts at390/768/1440 pixels. That is not a hosted mobile-device test. Cloud-browser viewport resizing was unavailable; hosted iOS/Safari, Android/touch, other engines, animation frame pacing, full screen-reader operation and manual contrast remain BLOCKED/NOT TESTED. Axe4.10.2 used WCAG2A/AA,2.1AA and2.2AA tags on six local states. It returned no supported violations but marked color-contrast incomplete on every state and additional aria/link rules incomplete on some pages. No WCAG conformance claim is made.

Dark mint styling was visually consistent across the observed pages. Dashboard values came from stored scans; no financial-loss claims, fake customer metrics, fake file trees or predicted-as-executed results were observed. Minor copy issue: ZIP reports carry a GitHub branch-identity limitation even when no repository ref was supplied; make that notice source-specific. That observation is not counted as an additional executed test.

## Security and operational limitations

This is a bounded technical review using authentication, session, authorization, input, upload, source-exposure and execution-safety themes from OWASP ASVS5.0.0 (https://asvs.owasp.org/). It is not a complete ASVS assessment or certification. No external systems were attacked. The live rate-limit check used one nonexistent synthetic email and11 sequential requests; no denial-of-service or credential-guessing campaign was performed.

Two distinct live principals, viewer/developer/admin role transitions, actual email/password recovery, MFA, private GitHub/OAuth, dependency-vulnerability scanning as a product feature, AI/prompt injection, live billing, PDF reports, restore drills, database failover, retention/deletion completion, worker restart recovery and complete secret-history analysis were not exercised. Disabled runtime/AI/payment features are not represented as verified capabilities. Local tenant/RBAC tests pass; the corresponding hosted two-user boundary remains a release gate.

## Required release gates

- FAIL: fix Review summary and named dialog, then run the new regressions.
- FAIL: normalize error security headers and evidence-pointer escaping.
- FAIL: fix authenticated landing CTA before usability sign-off.
- BLOCKED: provision isolated second-user/viewer test accounts and repeat the hosted tenant/RBAC matrix.
- NOT TESTED: backup restoration and operator account-recovery drill.
- BLOCKED: hosted mobile/touch and manual accessibility verification.
- NOT TESTED: eligible hosted scan cancellation, worker recovery, full error/network matrix and remaining state-changing controls.
- PASS: core supported static scan demonstrations, safe controls, report access, scoped resources, bounded upload/rate-limit tests, source/deploy commit identity, and existing automated regressions.

The current build is suitable for continued supervised internal evaluation. Reassess private beta after the failed and blocked release gates above are resolved. Keep public registration and live billing disabled.

## Reproduction and evidence

Run the ordinary suite with `.venv/bin/python -m pytest -q`. The added `tests/test_audit_regressions.py` contains two strict expected failures (headers and pointer) plus the passing database rate-limit boundary check. These are defects awaiting fixes, not suppressed success claims.

The supplemental browser script requires Playwright1.62.1, Chromium and `@axe-core/playwright`4.10.2, plus the disposable local QA account seeded by `python -m scripts.seed_local_qa` after local Alembic migration. With those packages available through NODE_PATH, run `node scripts/independent_browser_checks.cjs`. Optional `QA_CHROMIUM_MODULE` provides the existing trusted local Chromium adapter; `QA_AXE_MODULE` can select an absolute installed module path. The script returns nonzero when either UI regression is present. Do not seed production accounts with this local helper.

`scripts/independent_live_audit.py` is explicitly opt-in (`PREFLIGHT_AUDIT_APPROVED=1`), pinned to the named staging origin, and reads an ignored operator credential file without printing values. It creates retained synthetic data and consumes scan quotas. Do not rerun without confirming that scope and quota; it is not a generic external scanner. Supplemental live checks (rate limit/source exposure/export) are recorded as executed evidence; no real credentials are embedded in repository artifacts.

Evidence directory: [audit-2026-10-28](audit-2026-10-28/). It contains sanitized live API/browser results, supplemental UI results, regression JSON summary, local browser results, query profile, dependency audit, provider metrics summary and GitHub CI verification. Screenshot evidence was delivered separately in the audit conversation. No credentials or session cookies are included.

## Detailed live API assertions

| Feature | Observed evidence | State | Severity |
| --- | --- | --- | --- |
| Anonymous login page | HTTP 200; 3 sequential samples | PASS | — |
| Anonymous workspace gate | HTTP 303 redirect /login | PASS | — |
| Anonymous API denial | HTTP 401 | PASS | — |
| Closed registration | HTTP 403 | PASS | — |
| Live API login | HTTP 200 | PASS | — |
| Cookie security flags | Secure / HttpOnly / SameSite=Strict / 7-day lifetime | PASS | — |
| Missing CSRF rejected | HTTP 403 | PASS | — |
| Foreign Origin rejected | HTTP 403 | PASS | — |
| Controlled audit workspace | Created labeled synthetic organization f95c92d4-ae93-46b7-b788-fe3c10191e35 | PASS | — |
| Nonmember organization /repos | HTTP 404 | PASS | — |
| Nonmember organization /scans | HTTP 404 | PASS | — |
| Nonmember organization /dashboard | HTTP 404 | PASS | — |
| Nonmember organization /members | HTTP 404 | PASS | — |
| Nonmember organization /audit | HTTP 404 | PASS | — |
| Unsafe repository input http://127.0.0.1/private | HTTP 422 | PASS | — |
| Unsafe repository input https://github.com/a/b | HTTP 422 | PASS | — |
| Unsafe repository input a/b/../../x | HTTP 422 | PASS | — |
| ZIP traversal rejected ../escape.py | HTTP 422 | PASS | — |
| ZIP traversal rejected C:/escape.py | HTTP 422 | PASS | — |
| Malformed ZIP rejected | HTTP 422 | PASS | — |
| Malformed contract rejected | HTTP 422 | PASS | — |
| Known OpenAPI endpoint removal | 6505af7b-1f4e-42a4-8c46-ae2d23652f05: [(None, 'high')] | PASS | — |
| Access-controlled json export | HTTP 200; 2298 bytes | PASS | — |
| Access-controlled csv export | HTTP 200; 244 bytes | PASS | — |
| Anonymous report denial | HTTP 401 | PASS | — |
| Scan ID scoped to organization | HTTP 404; same owner, wrong organization | PASS | — |
| Unchanged contract safe control | 3b45cabd-0e2b-42cf-869d-b859446c6a42: 0 findings | PASS | — |
| Python removal and signature changes | d33bd4af-d00a-4c99-8aee-714e9e1a7b4c: [('Public function signature changed: public_api', 'medium'), ('Public module function removed: removed_api', 'high')]; both expected changes detected (medium signature, high removal); corrected overly strict two-high test oracle | PASS | — |
| Unchanged Python safe control | c0fdc15b-d488-40af-a8a2-dc6c77a7e3e5: 0 findings | PASS | — |
| Public GitHub branch comparison | 8ebf41f8-3818-4670-88e8-b1945117875c; main → main; status completed | PASS | — |
| Idempotency same scan returned | HTTP 202; stable job ID | PASS | — |
| Invalid ref produces honest failed scan | d68814fe-c545-4bdd-9394-6c77069c47f1; GitHub archive unavailable (HTTP 404); check public access, ref and rate limits | PASS | — |
| History includes controlled scans | HTTP 200; 6 scans | PASS | — |
| Dashboard aggregates real scans | HTTP 200; counts 6 | PASS | — |
| Authenticated page security headers | content-security-policy, x-frame-options, x-content-type-options, strict-transport-security, referrer-policy | PASS | — |
| Logged-out session replay denied | HTTP 401 | PASS | — |
| Anonymous errors carry security headers | HTTP 401; missing content-security-policy,x-frame-options,x-content-type-options,strict-transport-security,referrer-policy | FAIL | Low |
| Live bounded account login rate limit | [401, 401, 401, 401, 401, 401, 401, 401, 401, 401, 429]; Retry-After 900 | PASS | — |
| Source/secret path protected /.env | HTTP 404 | PASS | — |
| Source/secret path protected /.git/config | HTTP 404 | PASS | — |
| Source/secret path protected /static/%2e%2e/app/security.py | HTTP 404 | PASS | — |
| Provisioning secret absent from public assets | Exact known operator secret values absent; values never recorded | PASS | — |
| Account export works | HTTP 200; no password or session hash fields | PASS | — |

## Detailed live browser checks

| Feature | Observed evidence | State |
| --- | --- | --- |
| Refresh retains login | https://zevq-preflight-staging.onrender.com/app | PASS |
| Review summary renders selected inputs | Review visibly contains [object HTMLDivElement] four times | FAIL |
| Live contract scan and evidence expansion | https://zevq-preflight-staging.onrender.com/app#scan/66762936-5d5e-4f06-830e-6220fb91c697 | PASS |
| Browser JSON report download | Download completed; file path returned | PASS |
| Navigation Projects | Repositories | PASS |
| Navigation Reports | Scan history | PASS |
| Navigation Organizations | Team members | PASS |
| Navigation Audit log | Audit log | PASS |
| Navigation Settings | Workspace settings | PASS |
| Navigation Dashboard | Deploy with confidence | PASS |
| Documentation page | https://zevq-preflight-staging.onrender.com/docs | PASS |
| Public navigation Product | https://zevq-preflight-staging.onrender.com/features | PASS |
| Public navigation How it works | https://zevq-preflight-staging.onrender.com/how-it-works | PASS |
| Public navigation Security | https://zevq-preflight-staging.onrender.com/security | PASS |
| Public navigation Contact | https://zevq-preflight-staging.onrender.com/contact | PASS |
| Public navigation FAQ | https://zevq-preflight-staging.onrender.com/faq | PASS |
| Public navigation Use cases | https://zevq-preflight-staging.onrender.com/use-cases | PASS |
| Public navigation Pricing | https://zevq-preflight-staging.onrender.com/pricing | PASS |
| Public navigation Privacy | https://zevq-preflight-staging.onrender.com/privacy | PASS |
| Public navigation Terms | https://zevq-preflight-staging.onrender.com/terms | PASS |
| Public navigation Cookies | https://zevq-preflight-staging.onrender.com/privacy#cookies | PASS |
| Landing page | https://zevq-preflight-staging.onrender.com/ | PASS |
| Signed-in landing CTA returns to workspace | Authenticated session exists but CTA opens login form | FAIL |
| Destructive confirmation cancellation | Opened Delete account modal and cancelled; no deletion submitted | PASS |
| Organization switching | Dropdown switched to synthetic QA organization and settings updated | PASS |
| Dialog accessible name | Native confirmation dialog has no aria-label or aria-labelledby; heading is not associated | FAIL |
| Browser ZIP scan | Harmless safe.py uploaded; completed static report rendered | PASS |
