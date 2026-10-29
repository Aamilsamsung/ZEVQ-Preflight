# Email recovery and external monitoring

These integrations are implemented but disabled until configured and verified. Public registration stays disabled. No email delivery or external inbox receipt has been established by deterministic tests.

## Email

Use an approved SMTP provider with a verified sender, TLS465 or STARTTLS587. Store secrets only in Render's secret environment UI:

- `PREFLIGHT_EMAIL_ENABLED=1` only after approval/configuration
- `PREFLIGHT_SMTP_HOST`, `PREFLIGHT_SMTP_PORT` (465 or587)
- `PREFLIGHT_SMTP_USERNAME`, `PREFLIGHT_SMTP_PASSWORD`
- `PREFLIGHT_SMTP_FROM` (plain verified sender address)
- `PUBLIC_ORIGIN=https://zevq-preflight-staging.onrender.com`

Never paste credentials into chat or GitHub. No provider account was created or paid plan enabled. Confirm a test message reaches an authorized inbox, then test `/verify-email`, `/forgot-password` and `/reset-password`. SMTP submission is not inbox receipt. The test fixture's intercepted messages are not delivery evidence.

Only existing provisioned users are eligible. A trusted operator can use `python -m app.manage create-user --email BETA_EMAIL --identity-verified --require-email-verification` to create a pending account with an interactive password prompt; it cannot sign in until mailbox confirmation. This command does not send a message or enable registration. Legacy operator-attested verified users remain unchanged; this migration does not claim their ownership was newly verified by email. Verification links apply to unverified provisioned accounts. Links use fragments, require an explicit confirmation POST, expire in15minutes and are single use. SHA256 hashes only are stored. A successful reset revokes all sessions and invalidates outstanding links. Password changes and operator resets invalidate outstanding links too. Origin checks, database rate limits and generic account-independent responses apply. Messages contain no source code. Delivery errors have generic audit actions, never exception bodies or tokens.

Mail sends as an after-response task. Process termination can lose delivery; the user must request another link. There is no durable retry outbox. Earlier links are invalidated on resend. Recovery proves control of the mailbox, not identity beyond the mailbox. MFA remains unavailable.

## External monitor

`.github/workflows/availability.yml` is opt-in, intended for the existing repository. It does not run until repository variable `PREFLIGHT_MONITOR_ENABLED=true` is set. Scheduled workflows normally run from the default branch, so this unmerged implementation branch does not establish a deployed schedule. Review and owner authorization of the workflow placement are required. Do not merge unreviewed branches to activate it.

The script probes only the fixed staging HTTPS origin, rejects redirects, uses five-second request deadlines and validates response status. Three failed attempts separated by10seconds create one deduplicated GitHub incident issue; recovery comments and closes the existing issue. Issue text contains no tenant identities, code, credentials or raw remote errors. Configure repository watching/notification delivery and verify actual receipt through a synthetic incident before calling monitoring operational.

For worker/queue/database signals, generate a random32+character `PREFLIGHT_MONITOR_TOKEN` privately and set the same value in Render and GitHub Actions secret storage. `/api/operations/monitor` uses a constant-time Bearer check, returns404 if disabled/unauthorized, and reports aggregate booleans only:three scan failures in15minutes, running lease older than180seconds, queued job older than300seconds. It does not establish worker liveness when idle, and does not count every unrelated API500. Health/database failures are observed via probes. Full request error-rate monitoring remains incomplete.

GitHub issue creation is external notification evidence, not proof that the owner received an email/push. Neither a real incident issue nor real delivery has been executed in this increment. Schedules are best-effort and may be delayed; no SLA is claimed. A15-minute probe can keep free services awake or consume quotas; review budget before enabling. The workflow does not upgrade billing.

## Health check

`/health` now checks SELECT1 using a separate small connection pool, two-second connection timeout and PostgreSQL1.5-second statement timeout; errors return generic503. These are per-stage bounds, not a guarantee about network/proxy latency. It does not expose connection details. The Render provider setting must still be saved to `/health` by the owner and independently re-read. No outage has been induced on staging.
