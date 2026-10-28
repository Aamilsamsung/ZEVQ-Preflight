# Closed-evaluation release record

Status: **useful local MVP; free hosted staging awaits database connection; public launch NOT approved**.

Repository: https://github.com/Aamilsamsung/ZEVQ-Preflight
Branch: `implementation/secure-preflight`
Baseline: `3f3e1923d48831b8b314558eb57caac7b4517be2`
Final commit: the head containing this release record; consult GitHub's commit/CI record for its immutable SHA.
Live URL/deployed commit: **none**. No Preflight infrastructure was provisioned successfully.

## Implemented versus incomplete

| Area | Implemented | Incomplete/disabled |
|---|---|---|
| Authentication | Provisioned accounts, Argon2, opaque persistent sessions, expiry/revocation, logout/all | Automated verified-email signup/reset, OAuth, MFA, session UI |
| Tenant boundaries | Multiple organizations, switching, roles, scoped data, owner membership administration | Email invitations, ownership transfer, enterprise controls |
| GitHub | Public archives, base/head refs, fixed origins/redirect checks, bounded streams | Private App/OAuth, branch/commit pickers, PRs, webhooks, schedules, resolved immutable commit identities |
| Analysis | Python AST syntax/routes/public function changes, dangerous-call review, selected config diffs | JS/TS parsers, full type analysis, secrets rules, migration analysis, CVE database/lockfile verification |
| API contracts | Selected OpenAPI 3 JSON request/response/parameter/auth/status/schema checks; local refs | Full OpenAPI/JSON Schema validation, YAML, complex/dynamic schemas, dynamic FastAPI schemas |
| Evidence | Stable finding IDs, versioned rules, file/line, evidence, severity/confidence, actions, honest unknowns | Reviewer decisions, suppressions/expiry, false-positive workflow |
| Impact | Declared Python import evidence displayed | Resolved interactive runtime impact graph |
| Simulation | Explicit static-only/not-executed status | Runtime test execution and isolated execution sandbox; no predicted result is called executed |
| Jobs | Persistent states, per-tenant admission, claim locking, expired-lease recovery, cancellation, bounded child processes | General retry/backoff UI, schedules, heartbeat/alerting, retention policies |
| Workspace | Real-data dashboard, repositories, new scan, progress, history, evidence reports, team/audit/settings | Scan comparison/trends, approvals, notification center, full administrator console |
| Reports | Interactive web, private authenticated JSON/CSV exports, CSV formula neutralization | PDF, public/access-token sharing, reviewer annotations |
| AI | No external source transmission; scanner independent of AI | Provider integration/consent and evidence-citing assistant |
| CI | Tests on SQLite + PostgreSQL, migration cycle | Customer PR status/check integration, deployment policies |
| Notifications | Local UI status/errors | Email/Slack/Teams alerts, delivery preferences |
| Billing | No payments activated or collected | Subscriptions, entitlements, provider/webhooks/portal/history |
| Operations | Migration schema, liveness/database checks, staging Basic gate, runbook | Hosted deployment, backups/restore drill, monitoring/error alerts, production load testing |
| Commercial | Positioning/docs/support mail link, draft privacy/terms, limitations | Legal review, complete release gates, customer registration/launch approval |

## Verification evidence

- Original repository baseline: seven tests passed after dependency installation.
- Latest local suite before final record: 95 tests passed, one Starlette/httpx test-client deprecation warning.
- GitHub Actions run `40552949670` passed pinned installation, `pip check`, full regression suite, PostgreSQL 16 migration upgrade/downgrade/upgrade and PostgreSQL API tests at commit `384031f72e1ffefcffc28f0ff46ce7c18cb8ba7e`.
- Application commit `4a06fa7f93e34b2acc8e45d61807daef8d79d625` passed the final 95-test suite, PostgreSQL migration/API checks and all 32 real Chromium checks in [Actions run 40652078061](https://github.com/Aamilsamsung/ZEVQ-Preflight/actions/runs/40652078061). Subsequent release-record edits are documentation only.
- 32 actual Chromium checks passed locally and in GitHub Actions, zero console errors/exceptions. See BROWSER_QA.md.
- `pip-audit` checked 33 pinned dependencies: zero known vulnerabilities on 28 October 2026. This does not establish absence of vulnerabilities or certify security.
- Real GitHub archive retrieval at baseline SHA: seven supported files processed in 11.118 seconds, static result only. Network/provider timings are environment-dependent.
- Synthetic local CPU-only test, ten runs of 400 small Python files/signature changes: median 22.02 ms, maximum 51.41 ms, 400 findings. Excludes network, uploads, queue and database. No production throughput claim.
- Render Blueprint validated against Render's public JSON schema. No platform apply/deployment validation or live QA performed.

## Release gate checklist

| Gate | State | Evidence or blocker |
|---|---|---|
| Preserve existing repository/history | PASS | Incremental implementation branch |
| Core static analysis and evidence tests | PASS | Local regression suite |
| Unknown/skipped inputs disclosed | PASS | Coverage records and regression tests |
| Session/CSRF/role/tenant boundaries | PASS | Automated API tests; not independent certification |
| Durable PostgreSQL schema/API | PASS | CI PostgreSQL 16 and migration cycle at foundation commit |
| Final application CI | PASS | Application commit 4a06fa7; Actions run 40652078061 |
| Browser core flow/mobile/tablet/desktop | PASS | 32 local checks |
| WCAG 2.2 AA full assessment | NOT TESTED | Keyboard/overflow checks are partial |
| Hosted restricted staging | BLOCKED | Free single-service configuration prepared; connect a dedicated Free Neon PostgreSQL project |
| Deployed commit/HTTPS/browser workflow | BLOCKED | No live deployment |
| Backup restoration and production rollback drill | NOT TESTED | Runbook only |
| Monitoring, alerts, retention | FAIL | Not configured |
| Email signup/verification/recovery | FAIL | Disabled/incomplete |
| Authorized private GitHub integration | FAIL | Not implemented |
| Billing readiness | FAIL | Disabled/incomplete; no live charges |
| Privacy/terms professional review | NOT TESTED | Draft information pages only |
| Full commercial roadmap | FAIL | Matrix lists remaining work |
| Public registration and launch authorization | BLOCKED | Requires release gates and explicit owner approval |

## Security review scope

Tests cover cross-tenant reads/mutations, viewer restrictions, session expiry/revocation, CSRF/Origin rejection, login throttling, upload/stream bounds, ZIP traversal/symlinks/duplicates, fixed GitHub origins/redirects and CSV formulas. Static analysis never imports customer source. Frontend uses text nodes for untrusted evidence and restrictive security headers. Source payloads are cleared when jobs reach terminal states.

Remaining risks include incomplete independent security review, no MFA/password recovery flow, no automated backup/retention monitoring, no production load/abuse test, and no hosted encryption/backup configuration verification. Full ASVS compliance is not claimed.

Recommendation: **restricted evaluation with approved nonconfidential inputs after staging is provisioned and tested**. Do not market the full roadmap as available, collect live payments, or open customer registration yet. See OPERATIONS.md for provisioning, deployment, rollback and administrator setup.

## Free-hosting revision — 28 October 2026

The owner rejected paid hosting. Railway is excluded (expired trial). `render.yaml` now declares a single **Free** web service; no paid worker/database resource. `app.serve` supervises separate web/static-worker processes, applies migrations and terminates the web service if its worker exits. On-demand wake hints reduce idle external-database activity. New real-HTTP/process tests cover this setup. The original 95-test/32-browser evidence above predates this supervisor change; the updated branch CI must be checked before deployment.

A dedicated external Free PostgreSQL project is still required. The two existing Supabase projects remain untouched. A Neon connection was requested through the available integration; no Neon project or credentials have yet been obtained. Free services have sleep, shared resource and usage limits; this is protected evaluation capacity, not an always-on enterprise service. No paid resources, upgrade, or trial renewal is authorized.
