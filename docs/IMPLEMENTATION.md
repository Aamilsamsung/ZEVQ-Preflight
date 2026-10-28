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
1. IMPLEMENTED: PostgreSQL schema/migrations, provisioned verified accounts, revocable sessions, CSRF, tenant roles, protected staging.
2. IMPLEMENTED: durable static scan jobs, bounded GitHub download, history, reports, quotas, cancellation.
3. IMPLEMENTED: AST findings, OpenAPI compatibility, reproducible evidence and tests.
4. IMPLEMENTED: connected dashboard, repository/scan workflow, honest limitations/docs.
5. PARTIAL: regression/security and local browser checks passed; release record and runbook written. Free single-service hosting is prepared with process-separated static workers. Hosted protected staging is live on Render Free + dedicated Neon Free; Railway is excluded.
6. REMAINING release roadmap: email delivery/verification/reset, OAuth/App private repository auth, webhook/PR checks, isolated execution, billing, MFA, scheduled scanning, retention/backups, PDF, dependency advisory feed, JS/TS parsers, full graph, admin tools. Do not advertise these as complete.

Public customer registration and live payments remain disabled. No customer repository code is executed. No third-party AI transmission.

### Reference UI update — 28 October 2026

Rebuilt the authenticated workspace to follow the supplied dashboard reference: dark fixed sidebar, pale blue canvas, mint actions, glass-stack hero, recent-scan summary, four metric cards, scan table, severity donut, seven-day finding trend, quick actions, and latest findings. Existing repository, report, team, audit, settings and scan workflows remain connected. Dashboard charts and findings use organization-scoped stored data; no sample counts, artificial performance changes, compliance percentages, or execution results are displayed. The coverage panel describes actual supported capabilities. Search submits to filtered scan history. Mobile navigation remains collapsible; tables scroll within cards.

The dashboard API now returns seven daily aggregate counts and five recent evidence records, limited to the same latest-500 scan window as existing metrics. A regression test verifies these aggregates exclude another tenant's findings. The illustration is decorative CSS and does not represent an executed simulation.

### New Scan reference update — 28 October 2026

The New Scan route uses the second supplied dark reference: wider ink sidebar, mint active navigation, breadcrumb/header artwork, four-step progress strip, source tabs, live input preview, scope card, tip and bottom actions. Source, configuration and review are functional stages; submission starts the existing analysis and opens its real report. Configuration lists enforced release capabilities rather than offering unsupported execution modes. The preview shows selected repository/revisions or uploaded filenames/contract presence; it does not invent repository trees, file counts or timings. Private GitHub access remains unavailable. Back preserves inputs, refresh updates the preview and repeated submission is disabled while the request is pending. The prior light dashboard is preserved.
