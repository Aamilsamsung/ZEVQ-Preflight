# Public onboarding — prepared, disabled until release acceptance

Public registration does not become available merely because this code is deployed. Availability requires all of:

- `PREFLIGHT_REGISTRATION_ENABLED=1`
- valid TLS SMTP configuration with `PREFLIGHT_EMAIL_ENABLED=1`
- owner-reviewed legal text and `PREFLIGHT_LEGAL_APPROVED_VERSION=2026-10-29`

Leave these flags disabled until delivery,security,monitoring,recovery and owner legal review gates pass. Configuration validity is not proof of message receipt. Billing stays disabled. Marketing pages become anonymous only with the separate `PREFLIGHT_PUBLIC_ACCESS_ENABLED=1`;protected application APIs still require verified sessions and server-side tenant/role checks.

## Mailbox-first flow

`/register` takes an email and explicit consent to the current Terms/Privacy notice. It does not accept or store an attacker-selected signup password. The new account has an unusable random Argon2 hash,no organization,no session and no access. A single-use15-minute verification link lets the mailbox holder choose a14–256-character password. Verification sets access eligibility atomically and invalidates other links. An existing account/password is never overwritten by signup.

This prevents a pre-registration attacker from retaining a known password after the real mailbox owner confirms a link. Existing trusted provisioned-account verification remains compatible. The UI asks for a password on confirmation;public pending accounts are required to supply one server-side. No account is silently signed in by a verification GET. Tokens use fragments,are submitted by POST,and remain hashed at rest.

After verification,the user signs in and explicitly creates an organization. The existing role/tenant model applies. Team management currently adds existing verified accounts;email invitation/acceptance remains unavailable and must be resolved or explicitly excluded in the approved public scope.

## Protected acceptance before public launch

Keep `PREFLIGHT_PUBLIC_ACCESS_ENABLED` unset during staging. If registration is temporarily configured for an authorized email test,its POST requires the existing strong staging Basic credential as well as the email/legal flags. Supply credentials only through a secure operator/browser flow,never chat or committed files. Development tests use disposable databases and mocked email delivery;they do not establish received email.

`production` and `staging` modes both enforce PostgreSQL,strong protected-host configuration,Secure/HttpOnly/SameSite cookies and HSTS. Unknown mode names fail closed. The actual existing host mode is preserved. Do not use development mode for a public service.

## Abuse and data limits

Registration has database-backed5/IP/hour and shared3/mailbox/15-minute send limits. JSON authentication requests are limited to16KB,including streamed requests. Argon2 parameters are unchanged;at most two expensive operations execute concurrently per process,with a503 retry response when saturated. Signup hashing runs outside the async event loop.

New scans record the submitting account. The account has20 scans per rolling24hours across organizations,in addition to existing20/org/day and3 pending/org limits. PostgreSQL row locks serialize cross-organization account admission. Older scans retain NULL attribution;no historical attribution is invented. Those records continue to count toward the existing organization quota.

Terms acceptance and account email events are stored without tokens or source. Account export includes the latest1000 account events and states that limit. Account deletion removes those personal account events;existing organization deletion/ownership rules still apply. Existing records/passwords/organizations are not reset by migration0006.

Migration0006 adds nullable scan attribution,an existing-user pending default0,and account events. SQLite uses direct nullable-column addition to preserve scan/review rows,not batch recreation that could cascade deletes. PostgreSQL uses additive ALTER statements. Upgrade/downgrade tests run only in disposable databases;never downgrade live data as an application rollback.

## Remaining public acceptance

Real signup → received email → mailbox proof/password → login → organization → scan,and real password-reset/session revocation must be exercised against the deployed candidate. SMTP credentials/sender approval are still external prerequisites. Public capacity,proxy-aware rate limits,invitation consent,manual accessibility,external notification receipt,hosted recovery and legal/support readiness are not established by local tests. Do not enable public launch flags until the release report explicitly passes the mandatory gates.
