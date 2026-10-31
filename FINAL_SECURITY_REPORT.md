# Focused security verification — incomplete production acceptance

Verified 2026-10-31T18:31:02Z (1 November 2026, 00:01:02 IST).
Deployed commit e612f03dda7cd10d139ec4b95472ce978d5bf14c; application code matches CI candidate d2ae4d7603e8ea9cb8ec6e8c27e12609cff5a070. Render deployment dep-dbj34r7b9u1s73cu1qqg LIVE; release branch implementation/secure-preflight; development branch implementation/public-onboarding-20261029; https://zevq-preflight-staging.onrender.com; Neon schema0006. Documentation commit is the Git commit containing this report.

Confirmed on actual hosted APIs:tenant isolation and role restrictions,missing-CSRF/foreign-origin rejection,Secure/HttpOnly/SameSite session cookies,session revocation on logout,archive traversal rejection,protected report export,review-version conflicts and cross-tenant review denial. No customer code executed;only synthetic source/contracts and this owner's public repository inspected. Credentials remain in a local ignored0600fixture;no plaintext passwords,tokens,database URLs or private source are committed.

Candidate protections include mailbox-first gated registration,bounded Argon2 work,auth body limits,account/org quotas,hashed single-use email tokens,encrypted scoped private credentials and data-safe additive migration. Fresh local tests224pass/5skip;liveAPI55pass/0fail. Those checks are limited evidence,not a comprehensive penetration test. No fresh dependency-advisory database audit was run during recovery;older audit files remain historical evidence.

Remaining critical release gates:
- Render HTTP healthCheckPath is blank. Set /health on the existing service and read it back; endpoint itself returns200/database reachable. Connector has no service-settings update capability.
- Actual email delivery is disabled and unverified. Configure approved TLS SMTP sender through host secrets; prove received verification/resend/reset messages,expiry,password setup and revocation. Never paste secrets in chat.
- Private GitHub requires actual owner-authorized repository-restricted credential acceptance;fixture tests are not real authorization. GitHub App/OAuth remain unavailable.
- Actual external incident/recovery notification receipt is unverified. The monitoring schedule exists only on a non-default branch; main remains the original MVP. Do not claim scheduling or blindly replace main.
- Hosted browser/manual keyboard/responsive acceptance is blocked by environment:CUA cannot start due read-only sessions mount;local Chromium fails with socket Operation not permitted. Existing CI local-browser evidence is valid but is not current hosted browser acceptance.
- Isolated hosted restored-application journey is unverified because this runner cannot resolve Neon endpoints. Exact generated PostgreSQL migration DDL and record/constraint checks passed on the hosted snapshot;CI synthetic restore and rollback-app tests passed.
- Owner approval of current Terms/Privacy draft and public support/retention readiness remains required. No new legal approval is inferred.

Concurrency was checked repeatedly via branch heads,CI,deployment history,Neon operations and aggregate active connections. No unexplained activity was observed;termination of the old Work session cannot be proven. Future writes must use expected-head/SHA checks and stop on unexplained changes. No force push,live schema downgrade,customer data deletion,paid upgrade or public-launch flag activation occurred.
