# Getting started with protected evaluation

Access is provisioned by an administrator after identity verification. Public signup, email invitations and anonymous password recovery are not enabled. Sign in at the staging login page with the password supplied through your approved secure channel. Never send passwords in chat. Settings lets you change a known password and revoke all sessions; forgotten-password recovery uses the trusted operator procedure in OPERATIONS.md.

## Run your first static check

1. Select the intended organization in the sidebar. Reports, repositories and roles belong to that organization.
2. Open Projects to connect a permitted public GitHub `owner/repository`, or use New Scan → Upload Code / API / OpenAPI. Private GitHub credentials are not supported.
3. For GitHub, supply baseline and proposed revisions; immutable commit SHAs are preferable to moving branch names. For ZIP, choose a proposed archive and optional baseline archive. For API comparison, supply baseline/proposed OpenAPI3.x JSON.
4. Continue to Configuration. It lists supported static checks and execution restrictions; it does not enable an execution sandbox or external AI.
5. Review the actual input summary, then start once. The report shows durable queued/running/completed/failed state; refresh does not discard the job. Eligible queued/running jobs can be cancelled by an authorized writer.
6. Inspect each finding's rule, evidence, source location, severity, confidence, recommended action and coverage limitations. A clean result is not a guarantee of safety. Run your own tests and rollout checks separately.
7. Download authenticated JSON/CSV or return to Reports for history. Static comparisons are not executed tests. PDF and public share links are unavailable.

ZIPs are bounded and validated for archive/file sizes and unsafe paths. Unsupported or skipped files must be reviewed in coverage. Python AST and selected OpenAPI JSON compatibility rules are supported; JS/TS language parsing, full dependency vulnerability lookup and general migration safety are not yet supported.

## Review and compare findings

Owners, administrators and developers can record per-scan decisions with a reason. Viewers can read only. Suppression requires owner/administrator permission and a future expiry within90 days. Expired suppression is treated as open. Decisions retain original evidence and score, and history records earlier versions. If a concurrent reviewer changes the decision, reload after HTTP409 rather than overwriting it. See FINDING_REVIEWS.md.

Reports → Compare scan findings accepts two completed reports with matching source labels. Exact stable IDs identify newly observed, absent, changed or unchanged evidence. No longer observed does not prove fixed; changed locations/evidence/rules/inputs may change identifiers. Upload labels do not establish a shared project identity. Original reports remain authoritative. See SCAN_COMPARISON.md.

## Team access and support

Owners manage existing verified accounts and administrator/developer/viewer roles. Email invitations and ownership transfer are unavailable. A member's permissions are checked server-side on the next request. Select the correct organization before acting. Export needed reports before any irreversible organization deletion.

For support/security reports contact zevqlabs@gmail.com. Provide the generated X-Request-ID, approximate time, organization name through an approved private support channel, and a minimal reproduction. Do not include credentials, private repository source or sensitive production data. No incident-response SLA, certification or priority support entitlement is claimed.

## Evaluation data handling

Uploads are used for bounded static analysis; raw queued payloads are cleared on terminal processing/cancellation. Stored findings, evidence, review reasons and reports may contain project information. They require authenticated organization access and are retained until authorized deletion; automatic retention enforcement is not yet configured. Treat downloaded JSON/CSV as confidential. SQL parameters and raw URLs are omitted from the new structured logs, but platform log access/retention still need operational policy. Customer source is not executed or sent to external AI.

Use synthetic or approved evaluation inputs until private-beta release gates pass. Free-host cold starts and network delays may occur; no uptime or maximum-latency guarantee is provided.
