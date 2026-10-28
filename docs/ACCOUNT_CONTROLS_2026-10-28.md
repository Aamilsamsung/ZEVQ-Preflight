# Account controls and hosted isolation increment

This increment adds owner-managed role changes and membership removal controls to Team, authenticated password changes to Settings, and an operator-only password-reset command. Existing public registration, email delivery, OAuth, AI and live payments remain disabled. No schema migration is required.

Server-side authorization protects membership edits. An owner cannot change the owner role through this endpoint; viewers, developers and administrators cannot change roles or add/remove members. Demotions apply to existing sessions on their next request. Removing a membership does not delete the account or its other organizations. Audit events identify role changes and password changes/resets.

Password changes require the current password, enforce14–256 characters and a different new password, and revoke every session. Operator recovery requires explicit identity attestation and a non-secret support reference; secrets are entered through a terminal prompt. No anonymous reset endpoint was added.

Hosted baseline isolation verification used three newly provisioned synthetic accounts and two isolated QA organizations in the dedicated staging database.23 HTTPS checks passed: distinct-user cross-tenant reads, viewer mutation restrictions, privileged audit restrictions, private report protection and an actual completed contract scan. No customer account was granted access, and no real organization was modified. Synthetic fixtures are retained; credentials are generated and stored only in an ignored, permission-restricted artifact file. New role/password behavior must additionally be exercised after deployment.

Local API tests cover session revocation, old/new password authentication, reset attestation/auditing, short/reused password rejection, protected-owner restrictions, administrator/viewer boundaries, promotion/demotion on an existing session and removal. Supplemental browser tests cover role-editor persistence and password mismatch feedback. CI now includes these API cases on PostgreSQL and adds a guarded synthetic dump/restore exercise. Actual CI outcomes and hosted follow-up outcomes must be read from their execution records, not inferred from configuration.

The original live-audit report is historical evidence. Hosted two-principal isolation has now been exercised for its baseline read/write boundaries; hosted mobile/touch, manual contrast/screen-reader checks, provider-backed backup restoration, operator recovery exercise on the host, email delivery and MFA remain incomplete or not tested.

## Executed follow-up

Application commit `0ec00899b75006235d956b0cbd032b0d949ed910` is live in Render deploy `dep-dbgvlt5g1s2s73cdcpug`. GitHub run `40698349254`, job `122851059720`, completed successfully. Its decoded logs confirm116 Python passes (one PostgreSQL-only local skip),25 PostgreSQL passes,37 workflow browser passes and11 supplemental UI passes. The synthetic PostgreSQL restore step passed table-count, restored login, report and two-user isolation assertions.

The hosted follow-up with `PREFLIGHT_TEST_ACCOUNT_CONTROLS=1` completed31 assertions, all passing. It repeated the baseline boundaries and verified owner promotion to developer, a newly permitted repository write, demotion to viewer on the same session, self-promotion denial, password change, revocation of another active session and authentication with the new password. Only the generated synthetic viewer password changed. Real user credentials and memberships were not modified. Sessions created by the test were logged out afterward. The synthetic accounts and organizations are retained for repeat checks, with credentials excluded from Git.

Live cloud Chrome displayed the new password panel and keyboard navigation reached its Change password button. No real user's password was entered or changed through the browser. Operator reset was exercised in automated database tests; a real hosted operator recovery procedure remains not tested. These results do not establish hosted provider backup recovery, full WCAG conformance, MFA or public launch readiness.
