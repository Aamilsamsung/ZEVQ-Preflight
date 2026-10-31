# Secure owner setup — exact remaining actions

Prepared after Checkpoint6. No passwords,tokens,connection strings or SMTP values belong in chat,Git,issue comments or reports. Existing public launch flags remain disabled.

## 1. Render HTTP health setting
Open https://dashboard.render.com/web/srv-dbgr4v0n74is73d798e0/settings → Health Checks → Edit → set path `/health` → Save. Use existing Free service,do not change plan,repo,branch or startup command. Tell this Work session when saved so it can re-read provider configuration and inspect any resulting deployment before further mutations.

## 2. Email sender and delivery
Choose/approve your existing free SMTP provider and verify its sender. In the same Render service's Environment secret UI,configure `PREFLIGHT_SMTP_HOST`,`PREFLIGHT_SMTP_PORT`(465or587),`PREFLIGHT_SMTP_USERNAME`,`PREFLIGHT_SMTP_PASSWORD`,`PREFLIGHT_SMTP_FROM` and `PUBLIC_ORIGIN=https://zevq-preflight-staging.onrender.com`. Enable `PREFLIGHT_EMAIL_ENABLED=1` for protected acceptance. Preserve all unrelated variables and any existing encryption key. Keep `PREFLIGHT_REGISTRATION_ENABLED` and `PREFLIGHT_PUBLIC_ACCESS_ENABLED` unset/disabled. Do not invent SMTP credentials or use the Gmail connector as an SMTP password. Save/deploy through Render and report only that configuration is ready.

The connected owner Gmail inbox can then be checked for actual verification/reset messages. Received messages and complete password-reset/session-revocation journeys must pass;SMTP submission alone does not pass. Never forward bearer verification/reset links into chat. Public mailbox-first signup requires legal approval and a protected acceptance setup before launch flags.

## 3. Isolated recovery application acceptance
In Neon,select project `dawn-bonus-77001287`,branch `migration-0006-validation-20261031` / `br-orange-boat-b3dljf23`,database `neondb`,and its DIRECT connection endpoint `ep-dark-king-b3w2usjz.c-4.ap-southeast-1.aws.neon.tech`. This is the isolated snapshot,NOT staging. Copy the connection string privately.
Open https://github.com/Aamilsamsung/ZEVQ-Preflight/settings/secrets/actions → New repository secret → name `PREFLIGHT_RECOVERY_DATABASE_URL` → paste the snapshot URL into the secret value. Never create this as an ordinary variable or commit it. Tell Work the secret is ready. The isolated recovery workflow is prepared to fail closed until this prerequisite is available;Work can rerun its failed job after setup. It verifies schema0006,real application/session/static-worker/report/tenant behavior and unchanged original business-row fingerprints. It never downgrades,migrates,restores over staging or runs destructive pytest fixtures.

## 4. GitHub notification receipt
The real transport drill successfully created issue6,posted a recovery comment,and closed it. Connected Gmail had no matching notifications at observation. Open the repository's Watch menu and enable the notification events you want;review https://github.com/settings/notifications to ensure email delivery goes to your connected mailbox. Do not change unrelated account preferences. Tell Work when enabled so it can perform ONE new labeled incident/recovery receipt drill. Do not represent issue creation as inbox receipt. A new drill must use a new deliberate run;blind workflow retries are refused.

Recurring monitoring is not yet deployed:the existing availability workflow remains off the default branch and uses an opt-in repository variable. Default-branch placement and opt-in configuration must be reconciled without replacing the old main application blindly. The application/worker aggregate endpoint also requires the same32+character `PREFLIGHT_MONITOR_TOKEN` in Render and GitHub Actions secrets;never expose it. Health-only monitoring does not prove idle worker liveness or full APIerror-rate coverage.

## 5. Private GitHub acceptance
Preserve an existing `PREFLIGHT_CREDENTIAL_KEY` if present. If absent,generate a Fernet key privately on a trusted machine and store it only in Render's Environment secrets;enable `PREFLIGHT_PRIVATE_GITHUB_ENABLED=1` for the authorized test. Do not rotate an existing key casually.
Through GitHub's own token settings,create an expiring fine-grained token restricted to ONE private fixture repository with Contents read-only and required Metadata access. Enter it ONLY in the Preflight owner connection form,never chat. Use known safe/breaking revisions and report only repository name and readiness. Real scan/immutable revision evidence,isolation,disconnect and provider-side revocation must be verified. Connection in ChatGPT does not grant the SaaS a customer credential.

## 6. Authenticated hosted browser test
The anonymous CI browser runner now passes19checks. Authenticated workspace testing still requires a securely configured synthetic QA account for the runner or a working secure interactive browser. Do not put QA passwords/cookies in repository files or public workflow inputs. Existing local ignored fixtures are not GitHub Actions secrets. Keep current55hostedAPIchecks as completed evidence;they do not substitute for this browser gate.

## 7. Legal approval
Review the exact current Terms and Privacy drafts in `static/app.js` (also rendered at `/terms` and `/privacy` behind the staging gate). Approve or request changes explicitly before setting `PREFLIGHT_LEGAL_APPROVED_VERSION=2026-10-29`. This flag is not approval by itself. Public registration remains disabled until legal,email,security,monitoring,recovery and hosted acceptance gates pass. Billing stays disabled.

After setup,send only completed action names(no secret values). Work must first check remote heads/deployments for concurrent activity,then run only the newly unblocked acceptance tasks. No public readiness claim is authorized by setup alone.
