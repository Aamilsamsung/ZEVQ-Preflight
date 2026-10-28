# Account controls and hosted isolation increment

This increment adds owner-managed role changes and membership removal controls to Team, authenticated password changes to Settings, and an operator-only password-reset command. Existing public registration, email delivery, OAuth, AI and live payments remain disabled. No schema migration is required.

Server-side authorization protects membership edits. An owner cannot change the owner role through this endpoint; viewers, developers and administrators cannot change roles or add/remove members. Demotions apply to existing sessions on their next request. Removing a membership does not delete the account or its other organizations. Audit events identify role changes and password changes/resets.

Password changes require the current password, enforce14–256 characters and a different new password, and revoke every session. Operator recovery requires explicit identity attestation and a non-secret support reference; secrets are entered through a terminal prompt. No anonymous reset endpoint was added.

Hosted baseline isolation verification used three newly provisioned synthetic accounts and two isolated QA organizations in the dedicated staging database.23 HTTPS checks passed: distinct-user cross-tenant reads, viewer mutation restrictions, privileged audit restrictions, private report protection and an actual completed contract scan. No customer account was granted access, and no real organization was modified. Synthetic fixtures are retained; credentials are generated and stored only in an ignored, permission-restricted artifact file. New role/password behavior must additionally be exercised after deployment.

Local API tests cover session revocation, old/new password authentication, reset attestation/auditing, short/reused password rejection, protected-owner restrictions, administrator/viewer boundaries, promotion/demotion on an existing session and removal. Supplemental browser tests cover role-editor persistence and password mismatch feedback. CI now includes these API cases on PostgreSQL and adds a guarded synthetic dump/restore exercise. Actual CI outcomes and hosted follow-up outcomes must be read from their execution records, not inferred from configuration.

The original live-audit report is historical evidence. Hosted two-principal isolation has now been exercised for its baseline read/write boundaries; hosted mobile/touch, manual contrast/screen-reader checks, provider-backed backup restoration, operator recovery exercise on the host, email delivery and MFA remain incomplete or not tested.
