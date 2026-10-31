# Staging deployment verification

Verified 2026-10-31T18:31:02Z (1 November 2026, 00:01:02 IST).
Deployed commit e612f03dda7cd10d139ec4b95472ce978d5bf14c; application code matches CI candidate d2ae4d7603e8ea9cb8ec6e8c27e12609cff5a070. Render deployment dep-dbj34r7b9u1s73cu1qqg LIVE; release branch implementation/secure-preflight; development branch implementation/public-onboarding-20261029; https://zevq-preflight-staging.onrender.com; Neon schema0006. Documentation commit is the Git commit containing this report.

## Deployment evidence
- Existing workspace tea-dak1mgafngtc73ftfekg confirmed by user's execution attachment.
- Existing Free service srv-dbgr4v0n74is73d798e0,autoDeploy off,start python -m app.serve.
- Reviewed candidate is a direct descendant of93ec40a. Existing configured release branch fast-forwarded with expected_sha93ec40a and force=false to e612f03. No replacement infrastructure or unreviewed branch merge.
- Exactly one manual deployment triggered:dep-dbj34r7b9u1s73cu1qqg;started2026-10-31T18:24:44Z,finished2026-10-31T18:26:03Z,statusLIVE. Provider commit matches e612f03.
- /health returned statusok,version0.2.1,database reachable. /api/auth/email/status returned delivery_enabledfalse,registrationdisabled,legal_version2026-10-29.
- Schema0006 verified after startup;baseline records preserved before synthetic QA data.55fresh hostedAPIchecks passed.

## Recovery
Isolated Neon snapshot br-orange-boat-b3dljf23,parentLSN0/1F36F00,rehearsed exact0006PostgreSQL DDL and verified constraints/data. Prior0005predeploy/recovery branches retained. Candidate CI tested restored synthetic data and older-app compatibility. Do not downgrade or reset live data as application rollback. Previous live application:93ec40a / dep-dbhk5hajnfac73a7dao0;actual hosted rollback remains untested.

## Remaining
- Render HTTP healthCheckPath is blank. Set /health on the existing service and read it back; endpoint itself returns200/database reachable. Connector has no service-settings update capability.
- Actual email delivery is disabled and unverified. Configure approved TLS SMTP sender through host secrets; prove received verification/resend/reset messages,expiry,password setup and revocation. Never paste secrets in chat.
- Private GitHub requires actual owner-authorized repository-restricted credential acceptance;fixture tests are not real authorization. GitHub App/OAuth remain unavailable.
- Actual external incident/recovery notification receipt is unverified. The monitoring schedule exists only on a non-default branch; main remains the original MVP. Do not claim scheduling or blindly replace main.
- Hosted browser/manual keyboard/responsive acceptance is blocked by environment:CUA cannot start due read-only sessions mount;local Chromium fails with socket Operation not permitted. Existing CI local-browser evidence is valid but is not current hosted browser acceptance.
- Isolated hosted restored-application journey is unverified because this runner cannot resolve Neon endpoints. Exact generated PostgreSQL migration DDL and record/constraint checks passed on the hosted snapshot;CI synthetic restore and rollback-app tests passed.
- Owner approval of current Terms/Privacy draft and public support/retention readiness remains required. No new legal approval is inferred.

No public launch declared. Keep public access/registration disabled until mandatory acceptance and owner approvals pass.
