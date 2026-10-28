# Operator guide

## Architecture and deployment status

FastAPI serves a vanilla JavaScript/CSS frontend and tenant-scoped APIs. SQLAlchemy/Alembic manages PostgreSQL records. A separately launched Python worker claims durable jobs using a row lock/conditional update and runs the static analyzer in a bounded child process. Customer code is never imported or executed. This process separation is not a sandbox suitable for running customer tests.

The protected evaluation service is live at **https://zevq-preflight-staging.onrender.com** (Render `srv-dbgr4v0n74is73d798e0`, Free plan, Singapore). It uses dedicated Neon Free project `dawn-bonus-77001287`, staging branch `br-solitary-hall-b3y011t5`, PostgreSQL 16. Railway is excluded; no unrelated database was reused and no paid plan was enabled.

`app.serve` supervises separate web and static-worker processes in one Free web instance. It applies owner-only migrations and optional explicit closed-staging provisioning before starting them, and shuts down both if either exits. On-demand wake hints avoid continuous idle database polling. Durable jobs and reports stay in external PostgreSQL. This mode is for one host, not a multi-host worker fleet.

Actual configured base plans: **Render Free $0/month + Neon Free $0/month**. There is no paid worker, Render database or persistent disk. Render Free sleeps after 15 minutes without inbound traffic and shares the workspace's 750 monthly free instance hours. Existing services share those hours and other quotas. Neon also enforces Free compute/storage/transfer allowances. No keepalive service or paid overage/upgrade is configured by this application. Check platform quota/spend settings before exposing more traffic; Free hosting is restricted evaluation capacity, not an always-on commercial service.

Deployment is manual from `implementation/secure-preflight`. Render currently uses its default TCP health check; `/health` and authenticated `/api/ready` were verified over HTTPS. A platform HTTP health-check path is not configured by the limited creation tool. The initial live commit was `dc2c17b00939f0470ffe557f5828cab91214a7a6`; consult the final deployment record for subsequent application hardening.

Sources: https://render.com/docs/free and https://neon.com/docs/introduction/plans (checked 28 October 2026).

## Restricted deployment procedure

1. Reuse the dedicated Preflight Neon project and confirm it remains on the Free plan. Do not reuse an unrelated product database, purchase a plan, or renew Railway.
2. Ensure the exact tested branch/commit is in GitHub. Do not point deployment at the older main branch.
3. Create the single Free web service from the reviewed Blueprint and supply the dedicated external Free database connection. No resources named for other products should be changed.
4. `PUBLIC_ORIGIN` is `https://zevq-preflight-staging.onrender.com`. Supply the exact origin if intentionally changing the hostname. Keep `PREFLIGHT_MODE=staging` on both services. Store the generated `STAGING_PASSWORD` in the host secret store.
5. The supervisor applies `alembic upgrade head` before starting Uvicorn and the static worker. The worker tolerates database unavailability and retries. A coordinated maintenance window is necessary for future incompatible schema changes.
6. Configure platform health checks at `/health`. This is liveness only. Authenticated `/api/ready` checks database reachability; a worker heartbeat/alert is not yet implemented.
7. Normal access uses the provisioned application account at `/login`. Anonymous visitors can load the sign-in page/assets, but private pages redirect to sign-in and private APIs require a valid session. Public registration remains disabled. Legacy HTTP Basic access remains compatible for operator tooling; it is not required for account sign-in.
8. The initial closed-evaluation account is already provisioned. Application email: `zevqlabs@gmail.com`; password: Render `PREFLIGHT_BOOTSTRAP_PASSWORD`. Retrieve values from your own Render Environment settings, not from source files. For additional attested accounts, from a trusted operator shell with the staging database environment, run `python -m app.manage create-user --email YOUR_VERIFIED_EMAIL --organization 'ZEVQ Labs' --identity-verified`. Password input uses a terminal prompt, not a command argument. Never commit operator credentials.
9. Verify unauthorized access is rejected, sessions persist across refresh, source comparisons finish, private reports require membership, and the deployed SHA matches the reviewed commit.
10. Run browser checks on the deployed URL. Do not approve public launch from local checks alone.

The Blueprint uses manual auto-deploy settings and contains no managed paid database or worker resource. Applying it is an infrastructure action, not a public launch approval.

## Worker behavior and limits

- One job per worker process. The Free instance runs a single web process, a worker process and at most one bounded static-analysis child. These share the free memory/CPU allocation. PostgreSQL locking supports multiple worker instances; concurrency has not been load-tested.
- Per organization: three pending jobs, 20 scans per rolling day, 20 connected repositories.
- Compressed archive limit 8 MB, selected UTF-8 sources at most 400 files, at most 300 KB per file, extracted selected content at most 8 MB.
- HTTP bodies are bounded, including chunked requests. These are application limits, not full infrastructure DDoS protection.
- Static job timeout 120 seconds; calculation timeout 90 seconds; Linux child CPU limit 60 seconds and address-space limit 768 MB. Hosting may enforce a lower memory cap.
- In supervised on-demand mode, queued submissions and status reads signal the local worker. It drains pending jobs, performs a startup lease-recovery sweep, and otherwise avoids idle database polling. Sleep/restart can delay progress; status polling or restart resumes eligible durable jobs.
- Leases expire after 180 seconds. Restart recovery requeues expired work up to three claims; exhausted jobs fail. General network-error retry/backoff and a retry UI are incomplete.
- Cancellation prevents publication of a cancelled job's result. It does not immediately terminate a child process; the bounded child may finish and have its result discarded.
- Uploaded source is stored in the database while queued/running, then payload is removed on completion, failure or cancellation. Database backup copies may retain older data. Timed retention policies are not yet implemented.
- Reports/evidence are tenant-scoped. Source paths and schema evidence can be sensitive. Evaluate with synthetic or approved nonconfidential source until hosting/retention reviews are complete.

## Recovery and rollback

These procedures are documented, **not verified against a hosted service**.

Before any production migration, stop writes or coordinate an appropriate snapshot, take an encrypted database backup with `pg_dump --format=custom`, and test restoration into a separate disposable PostgreSQL database with `pg_restore`. Compare row counts and run representative report retrieval and tenant boundary tests against the restored copy. Keep backup access separate from application credentials. Retention, scheduling and alerting require explicit configuration.

For an application rollback, stop/disable new admissions, drain or stop workers, redeploy the previous tested application commit to both web and worker, and retain the compatible schema. Do not blindly run `alembic downgrade base`: it drops all application tables and data. If a migration is incompatible, restore a verified backup into a separate database and point a coordinated web/worker deployment at it. Never repoint to an unrelated product's database.

The initial migration was tested in CI with upgrade/downgrade/upgrade on a disposable database; that does not test disaster recovery or a production rollback.

## Security and account administration

Identity provisioning is operator-attested; email delivery/verification/reset and MFA are pending. Public registration is deliberately closed. Privileged access should remain restricted to trusted evaluators.

Sessions are opaque, hashed in the database and revocable. Staging cookies are Secure/HttpOnly/SameSite=Strict. Mutations require CSRF tokens and reject mismatched Origin headers. No permissive CORS is configured. Organization membership and role checks run server-side; report links are authenticated API URLs, not public share tokens.

Account export includes account identity and memberships. Organization reports are exported separately. Owners must delete owned organizations before account deletion. Organization deletion cascades to memberships, repositories, scans and organization audit events. Customer-facing ownership transfer is not yet implemented.

Logging currently uses server/worker logs; external error tracking, structured event correlation, worker-health alerts and tested backup automation are pending. No ASVS certification or full independent security assessment is claimed.

## Dedicated Neon setup

The dedicated Free Neon project is `dawn-bonus-77001287` (Singapore, PostgreSQL 16); no existing product database is used. `DATABASE_URL_UNPOOLED` is the direct migration-owner connection. `DATABASE_URL` is the pooled restricted `preflight_runtime` role. The role has application-table DML and schema usage, without superuser/create-role/create-database/schema-create privileges. Migrations remain owner-only.

The optional closed-staging bootstrap reads `PREFLIGHT_BOOTSTRAP_EMAIL`, `PREFLIGHT_BOOTSTRAP_PASSWORD` and `PREFLIGHT_RUNTIME_PASSWORD` from the host secret store. This provisions only the operator-attested evaluation account. It does not send a verification email or enable public signup. Existing accounts are never reset on restart. The supervisor strips migration/provisioning secret variables from the web/worker child environments. Operators can retrieve the initial account password from their own Render environment settings; credentials are not committed or included in reports.

## Password changes and operator recovery

Settings provides an authenticated password-change form. It requires the current password, a different new password of14–256 characters, CSRF protection and rate limiting. A successful change revokes **all** sessions, including the current session, and requires sign-in again. This does not send email or enable anonymous recovery.

For a verified recovery request, use a trusted operator shell connected to the dedicated staging database:

```sh
python -m app.manage reset-password --email VERIFIED_ACCOUNT_EMAIL --identity-verified --reference SUPPORT_TICKET_ID
```

The operator must independently verify ownership before asserting `--identity-verified`. Use a non-secret ticket reference of3–64 letters/digits/dots/underscores/hyphens. The command prompts twice for the new password, updates its Argon2 hash, revokes all sessions, and records recovery events for the user's organizations. Never pass the password as a command argument or put it in logs. Changing Render's bootstrap password alone still does not reset an existing account. Email delivery and MFA remain unavailable.

Owners can change non-owner membership roles and remove memberships from Team. Existing sessions use the new permissions on their next request. Role changes cannot grant ownership or change the current owner; ownership transfer remains a separate incomplete feature. Administrators can read audit logs but only owners manage membership.

## Synthetic CI restore verification

The pipeline dumps its disposable PostgreSQL16 test database into temporary runner storage, restores into a separate `preflight_restore` database, compares table counts and verifies restored login, report evidence and two-user isolation. `scripts/backup_restore_check.py` refuses other database names, non-local hosts or execution outside CI. Only the summary is retained as an artifact; the database archive is not uploaded.

This tests the dump/restore toolchain with synthetic fixtures. It does **not** verify Neon point-in-time recovery, live backup retention, encryption/key recovery, production recovery time, or a hosted disaster-recovery drill. Those remain separate release gates.
