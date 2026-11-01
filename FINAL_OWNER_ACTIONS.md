# Remaining owner actions

No secret values belong in chat, ordinary repository variables, source, issue comments or reports. Do not enable public registration yet.

| Action | Exact location/value | Why owner input is needed |
|---|---|---|
| Set HTTP health path | Existing Render service → Settings → Health Checks → `/health` → Save | Available connector cannot edit service health settings |
| Configure mail | Existing service Environment: approved `PREFLIGHT_SMTP_HOST`, port 465/587, username, password, sender; correct `PUBLIC_ORIGIN`; protected email enable flag | Provider credentials and verified sender are not available here |
| Prepare recovery secret | Repository Actions secret `PREFLIGHT_RECOVERY_DATABASE_URL` from isolated branch `br-orange-boat-b3dljf23`, direct endpoint/database in OWNER_SETUP_ACTIONS.md | Available GitHub connector cannot write secrets |
| Prepare browser fixture | Repository Actions secret `PREFLIGHT_HOSTED_BROWSER_FIXTURE` using the synthetic identity/UUID JSON in AUTHENTICATED_BROWSER_ACCEPTANCE.md | No approved CI credential transport is configured |
| Verify notification destination | Repository Watch preferences and GitHub account notification email settings | Issue transport passed but inbox receipt did not |
| Authorize private fixture | Preserve host encryption key; enter one expiring fine-grained Contents-read token only through the SaaS owner form | A real customer authorization cannot be fabricated or borrowed from ChatGPT |
| Review legal/support draft | LEGAL_DRAFT_FOR_OWNER_REVIEW.md and LEGAL_OPERATIONAL_FACT_REVIEW.md | Owner approval, retention/support decisions and legal review are not granted by a flag |
| Authorize launch later | Explicit approval after all technical gates pass | This attachment requires a final separate launch authorization |

Full links/step sequence: OWNER_SETUP_ACTIONS.md. Browser JSON and expected prepared scan/review: AUTHENTICATED_BROWSER_ACCEPTANCE.md.

After secure setup, report only which actions are complete. Work must recheck remote heads/deployments/schema, then commit fresh recovery/browser request markers at the current head. Do not blindly rerun an old job after newer commits. Perform only newly unblocked acceptance; preserve passing evidence.

Do not casually rotate `PREFLIGHT_CREDENTIAL_KEY`, expose bearer links, upgrade plans or overwrite old main. Recurring monitoring still requires safe reviewed default-branch reconciliation and opt-in configuration; do not claim it is operating merely because the drill passed.

Deployment/configuration observation: the latest bounded email-status read timed out after 15 seconds. Provider still reports the same live deployment; this does not establish an outage or successful warm application acceptance. Do not retry unchanged requests indefinitely. Configure the HTTP health path and inspect actual provider logs as needed.
