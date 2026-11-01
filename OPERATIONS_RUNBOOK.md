# Operations runbook

- Live URL: https://zevq-preflight-staging.onrender.com
- Deployed application: `e612f03dda7cd10d139ec4b95472ce978d5bf14c`
- Render deployment: `dep-dbj34r7b9u1s73cu1qqg` — live
- Render service: `srv-dbgr4v0n74is73d798e0`, Free, automatic deployment off
- Configured release branch: `implementation/secure-preflight`
- Active development branch: `implementation/public-onboarding-20261029`
- Neon project: `dawn-bonus-77001287`; live migration: `0006`
- Report commit: the Git commit containing this file.

## Before any change

1. Read remote development/release heads, recent Render deployments and Neon migration state.
2. Compare with the expected checkpoint. Stop and report unexplained activity; the old Work session's termination cannot be proven.
3. Use expected-head guards. Never force-push, reset newer work, rotate keys casually, or queue a second overlapping deploy.
4. Record the exact intended source, backup/recovery reference and acceptance plan. Use existing Free resources only.

## Availability and startup

Check provider deployment state and sanitized application logs. Distinguish a Free-service cold start or runner timeout from a confirmed application failure. A healthy response does not prove all workflows.

The normal start command is `python -m app.serve`: apply additive migrations, preserve bootstrap accounts, then supervise API and static worker. The provider HTTP check must point to `/health`; the endpoint checks database reachability with bounded connection/query behavior. Independently read the provider setting after saving it.

Do not change staging to development mode or disable TLS/session controls to fix access. Never print database URLs, headers, credentials, signed archive URLs, mailbox links or customer source.

## Job failures

Inspect status and sanitized request/job references. Worker leases are 180 seconds with at most 3 attempts; analysis has a 90-second task bound and a 120-second supervised process bound. The supervisor must not leave an API-only service looking healthy after worker exit.

Use supported application cancellation/retry procedures only for authorized jobs. Do not run customer programs, shell commands, or arbitrary SQL from uploaded source. An idle queue does not prove worker liveness.

## Authentication and email

Keep public access/registration gated during acceptance. Store approved sender settings only in Render secrets. Verify received verification, resend, expiry, password setup/reset and session revocation; SMTP submission is insufficient. Email delivery is an after-response task and can be lost if the process stops; there is no durable retry outbox.

Never reset an existing user's password merely for QA. Any trusted operator recovery requires specific authorization, verified ownership and a non-secret support reference. Do not expose verification/reset bearer links in chat, logs or reports.

## Private repositories

Preserve the existing encryption key. Use one expiring, read-only fine-grained repository credential through the owner form. A SaaS disconnect does not revoke the provider token; revoke it separately in GitHub. Do not reuse ChatGPT connector authorization as a customer SaaS credential.

## Retention and deletion

Scheduled cleanup is disabled. Owner-configured manual cleanup uses a dry-run preview, up to 100 eligible terminal scans and a 10-minute preview expiry; records with review history are preserved. Do not run live cleanup as a release test.

Organization/account deletion affects live records and requires the authorized user flow. Deletion from the active database is not a verified promise of immediate erasure from all backups or isolated recovery copies. Account events export is bounded; state that limit honestly.

## Recovery and rollback

Use only the named isolated snapshot for acceptance. Configure the recovery Actions secret securely, create a fresh current-head run request and inspect sanitized results. Never redirect staging to the snapshot or downgrade schema 0006 as a test.

**Do not blindly roll back to the historical Render artifact:** it does not contain migration 0006. Prepare a new, separate source directory:

```bash
python -m scripts.prepare_rollback_bundle --destination ../preflight-rollback-0006
```

The builder refuses existing destinations and performs no database or deployment changes. It archives exact application 93ec40a, retains current migration history and dependencies, and writes a manifest. Review the bundle, new-feature compatibility and supported jobs before using the normal guarded release process on the existing service. Preserve schema 0006. Dedicated disposable PostgreSQL/SQLite startup tests passed; actual hosted rollback remains unperformed.

## Monitoring and support

Review health, protected aggregate queue/failure signals and tenant-scoped notifications. Do not mistake issue creation for owner inbox receipt. Label deliberate drills clearly; do not induce a real outage. Verify receipt and recovery after notification preferences change.

Support/disclosure contact currently implemented: zevqlabs@gmail.com. Ask for scan/request references and sanitized reproduction steps, not secrets or confidential source. Record incident scope, affected function, mitigation and actual verification; no unimplemented response-time guarantee.

## Public release

All mandatory email, private-feature scope, browser, recovery, monitoring, health, security and legal gates must pass. Then request separate explicit public launch authorization. Legal approval alone does not authorize launching. Keep billing disabled; do not promise guaranteed availability on Render Free.
