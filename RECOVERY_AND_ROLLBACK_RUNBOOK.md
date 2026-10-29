# Recovery and rollback runbook

29 October 2026. Live deployment remains5e0e211 / dep-dbh4jk6c6qcc73cihja0 / schema0003. Candidate d52fead includes additive0004/0005; it has not been deployed.

## Executed hosted preparation

Existing Neon Free project `dawn-bonus-77001287`, PostgreSQL16, has a21600-second history window in current provider metadata. Never assume that this makes an old recovery point available indefinitely.

The live branch is `br-solitary-hall-b3y011t5`. Snapshot branch `br-orange-water-b36lbess` copies parentLSN `0/1DC1868`, provider source timestamp2026-10-29T01:37:32Z (07:07:32 IST), created01:37:53Z. It has no compute. A direct query correctly failed `endpoint not found`.

Queryable child `br-mute-bread-b3znuqmn` was then created from that frozen copy, with0.25CU min/max and no paid-plan change. Compute `ep-floral-shape-b3yu1v7k` reported started01:50:18Z. An explicit suspend-interval request was rejected by the Free account; no paid setting was enabled. The provider's default settings were retained. Verify actual compute usage in Neon before leaving a rehearsal environment active; free allowances are finite.

Read-only count and content-fingerprint comparisons matched on all11 tables:4 users,4 organizations,5 memberships,9 sessions,5 repositories,25 scans,3 reviews,53 review events,91 audit events,1 retention policy and1 cleanup preview. Schema0003 matched. No raw passwords, tokens, source or report contents were exported for this comparison.

This establishes an accessible hosted point-copy with matching stored records. It **does not** establish restored login, tenant API behavior, queued-job execution, host failover or service rollback. The runner could not resolve the child PostgreSQL hostname (`gaierror`); no connection-string credential was retrieved to work around this. MCP read-only SQL remains available.

RPO/RTO:the provider reported a source point21seconds before snapshot creation. This is source-point lag, not a demonstrated disaster RPO. Full application recovery time has not been measured. Branch creation/compute start timestamps are not application RTO.

## Next authorized isolated rehearsal

1. Keep Render's live database URL unchanged. Use a trusted runner with TLS-validated access to the **queryable child**, never the live branch. Retrieve its restricted connection only through secure provider/runner secret storage; do not copy a database URL into chat or committed files.
2. Confirm project, branch, endpoint and `preflight` database identity against the IDs above. Stop if they differ. Use a separate process and bind any test API only to loopback or restricted staging access.
3. Record schema and count fingerprints before changes. Verify the copied synthetic owner/viewer/outsider accounts only. Test existing synthetic sessions, login, report JSON/CSV, scan history, review history, retention policy/preview and audit access. An outsider must receive404 for the other tenant's report.
4. Confirm no unrelated active jobs exist on the copy. Submit and execute a known static OpenAPI fixture; verify queued/running/completed states and simulation `not-executed`. Do not import source or execute customer tests. Record queue/execution timing. Distinguish a newly queued job on the restored target from a job already queued at the recovery point.
5. On a separately restored copy, validate the new additive migrations0004/0005 before any application promotion. Preserve existing rows and runtime grants. Do not downgrade, restore over or truncate the live database.
6. Load exact fallback source `9e78cde832e0d9213aae6450c5fb7d80f90ff6f4` in another process. Verify session/report/history/tenant behavior and execute its own synthetic static job. Do not run its migration downgrade command. Current CI already passes these checks against restored schema0005; hosted behavior remains to be exercised.
7. Preserve a sanitized result summary and measured application-ready time. A real live-service rollback remains a separate consequential action requiring explicit authorization; none was performed here.
8. Once evidence is accepted and removal authorized, delete only the two rehearsal branches in child-first order. Never delete/reset/default-switch the live branch. Copied sessions and credentials deserve the same access protection as the source while copies exist.

## CI recovery evidence

The pipeline runs actual pg_dump/pg_restore into `preflight_restore` on disposable local PostgreSQL16. It checks table counts, an existing synthetic session, password login, reports, reviews/history, retention policy/preview, tenant isolation and a restored queued static job. A separate process imports the exact fallback source and now also executes its static worker successfully against additive schema0005. The helpers require CI, localhost and the exact disposable database name. They are deliberately not commands to run against Neon.

See final QA report for latest run ID. Success here is not a hosted restore or an independent backup strategy. The isolated Neon copies share the same provider/account failure domain. Long-term independent backup automation and restore drills remain incomplete.

## Deployment rollback procedure (not executed)

Verify a safe backup and previous-source compatibility first; freeze unrelated writes only through an explicitly approved maintenance procedure. In Render, select the retained successful deployment for rollback or deploy an approved exact fallback commit. Confirm the artifact is retained and current service settings remain correct. Do not assume deployment rollback reverses SQL migrations, job side effects, secrets or external writes. Inspect `/health`, saved provider health path, authenticated tenant flows and worker completion after traffic moves. Record the resulting deployment/commit and retain schema changes unless an independently approved database recovery is needed.


Private credentials additionally require the original host encryption key,kept separately from database backups and never put into this report. Older fallback code does not support private payloads:current CI verifies a safe failed state without report publication at schema0005. Drain/cancel private jobs before an approved rollback;do not call that failure a successful private scan. Existing hosted snapshot branches remain schema0003 and have not been migrated.
