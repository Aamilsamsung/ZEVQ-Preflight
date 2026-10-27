# Implementation tracker — 2026-10-27

Baseline: 3f3e192; seven tests passed after a fresh dependency installation.
Audit: all original Python, HTML, requirements, workflow and deployment files read.

## Audit findings
- No authentication, tenant boundary, database, migration, queue or persistent reports.
- GitHub response fully buffered before size validation (resource exhaustion).
- Regex route detection produces misleading matches in comments/strings.
- ZIP silently omits unsupported/oversized sources; incomplete coverage not exposed.
- Unrestricted public scanning endpoint; no quotas or admission control.
- Existing CI tests seven small static cases, no HTTP/security or browser tests.
- No code execution or AI integrations (safe static-only behavior to preserve).

## Ordered increments
1. IN PROGRESS: PostgreSQL schema/migrations, provisioned verified accounts, revocable sessions, CSRF, tenant roles, protected staging.
2. IN PROGRESS: durable static scan jobs, bounded GitHub download, history, reports, quotas, cancellation.
3. IN PROGRESS: AST findings, OpenAPI compatibility, reproducible evidence and tests.
4. IN PROGRESS: connected dashboard, repository/scan workflow, honest limitations/docs.
5. TODO: regression/security tests, restricted deployment, browser QA and release record.
6. BLOCKED release roadmap: email delivery/verification/reset, OAuth/App private repository auth, webhook/PR checks, isolated execution, billing, MFA, scheduled scanning, retention/backups, PDF, dependency advisory feed, JS/TS parsers, full graph, admin tools. Do not advertise these as complete.

Public customer registration and live payments remain disabled. No customer repository code is executed. No third-party AI transmission.
