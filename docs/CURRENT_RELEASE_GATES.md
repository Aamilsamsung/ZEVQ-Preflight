# Current release gates — recovered 31 October 2026

This supersedes the 29 October live-state summary. Public beta remains NOT VERIFIED.

## Current evidence
- Latest code candidate: d2ae4d7603e8ea9cb8ec6e8c27e12609cff5a070 on implementation/public-onboarding-20261029 (draft PR4). Recovery documentation commits follow it; do not deploy main or the older secure-preflight branch by mistake.
- GitHub Tests runs 40883465251 and 40883454863 succeeded for that exact code candidate. Inspected job123480834266: dependency consistency, SQLite, PostgreSQL migration/API boundaries, synthetic backup/restore, previous-app rollback compatibility, monitor checks and real local browser workflows all succeeded.
- Fresh recovery runner: 224 Python tests passed,5 skipped;8 deterministic monitor checks passed;JavaScript syntax and Python compilation passed. Skips are not passes. No fresh hosted acceptance is implied.
- Read-only Neon inspection: staging br-solitary-hall-b3y011t5 is at schema0005,with email_tokens and repository_credentials present. Candidate migration0006 has NOT been applied. account_events is absent,as expected for0005.
- Render deployed application commit/health settings remain UNKNOWN in this recovery. Connector has no selected workspace. Its access rules require user confirmation of the listed Aamil's workspace tea-dak1mgafngtc73ftfekg. A bounded direct health request timed out after20seconds;this runner result is not proof of a service outage.

## Essential release sequence
1. Confirm Render workspace;read service/deploy metadata and logs once. Verify correct branch/commit,free plan,start command and /health before deployment.
2. Review PR4/current diff and select verified candidate on the existing service. app.serve performs additive migration0006 at startup;preserve current data and never downgrade the live schema.
3. Verify hosted login/session,organization isolation,ZIP/public GitHub scans,worker completion,finding reviews/history/report journeys. Private repository access requires real scoped authorization acceptance before advertising it.
4. Configure approved TLS mail sender through host secret controls;verify actual received signup and reset messages,password setup/login and session revocation. Local mocked delivery is insufficient.
5. Verify external alert delivery and recovery;scheduled workflow must be present on the default branch before scheduled execution can be claimed. main currently contains only the original MVP;do not merge it blindly.
6. Verify hosted restored-application behavior on isolated recovery data,public capacity and legal/support readiness. Email invitations remain unavailable;decide explicit beta scope before claiming team invitations.
7. Enable public access/registration only after these gates pass. Preserve disabled billing and untrusted execution.

No database writes,plan changes,public launch flags,merges or deployments were performed during recovery. Exact original48-hour deadline start was not available;do not reset it or promise unattended continuation.

Recovery checkpoint: ../RECOVERY_CHECKPOINT_2026-10-31.md
