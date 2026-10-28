# Operator guide

## Architecture and deployment status

FastAPI serves a vanilla JavaScript/CSS frontend and tenant-scoped APIs. SQLAlchemy/Alembic manages PostgreSQL records. A separately launched Python worker claims durable jobs using a row lock/conditional update and runs the static analyzer in a bounded child process. Customer code is never imported or executed. This process separation is not a sandbox suitable for running customer tests.

There is currently **no deployed Preflight service or live application URL**. Render rejected a dedicated free database. The connected Supabase account already has two active projects; neither is reused or changed. Railway is excluded because its trial has expired.

The deployment configuration now uses **one Free Render web service** in Singapore and a dedicated external Free PostgreSQL database (Neon Free proposed, connection not yet confirmed). Web and static worker run as separate subprocesses in that single free container. The supervisor shuts down both if either exits. An on-demand local wake marker avoids continuous idle database polling. Job data remains durable in PostgreSQL; the marker is just a wake-up hint. This mode is for one service instance, not a multi-host worker fleet. Existing `python -m app.worker` polling mode remains available for independently hosted workers.

No paid compute, paid worker, Render Postgres, persistent disk, upgrade or paid trial renewal is requested in `render.yaml`. The earlier $13 paid proposal was rejected and superseded. Neon Free has published hard usage allowances; capacity must be verified after connecting its account. Render Free sleeps after 15 minutes without inbound traffic, can lose local files on restart, and shares its workspace's 750 monthly free instance hours. External PostgreSQL preserves sessions/jobs/reports. Existing services share those hours and other platform usage limits; free hosting is a restricted evaluation environment, not an always-on commercial deployment. Check included bandwidth/build quotas before deploying; do not enable paid upgrades or overages.

Sources: https://render.com/docs/free and https://neon.com/docs/introduction/plans (checked 28 October 2026).

## Restricted deployment procedure

1. Connect Neon and verify its Free plan/capacity, then provision a dedicated Preflight project; alternatively supply a dedicated existing Free PostgreSQL database. Do not reuse an unrelated product database, purchase a plan, or renew Railway.
2. Ensure the exact tested branch/commit is in GitHub. Do not point deployment at the older main branch.
3. Create the single Free web service from the reviewed Blueprint and supply the dedicated external Free database connection. No resources named for other products should be changed.
4. Supply `PUBLIC_ORIGIN` as the exact HTTPS staging origin. Keep `PREFLIGHT_MODE=staging` on both services. Store the generated `STAGING_PASSWORD` in the host secret store.
5. The supervisor applies `alembic upgrade head` before starting Uvicorn and the static worker. The worker tolerates database unavailability and retries. A coordinated maintenance window is necessary for future incompatible schema changes.
6. Configure platform health checks at `/health`. This is liveness only. Authenticated `/api/ready` checks database reachability; a worker heartbeat/alert is not yet implemented.
7. Use HTTP Basic username `staging` and the generated password to access staging. Account sign-in remains a second separate requirement. Public registration remains disabled server-side.
8. From a trusted operator shell with the staging database environment, run `python -m app.manage create-user --email YOUR_VERIFIED_EMAIL --organization 'ZEVQ Labs' --identity-verified`. Password input uses a terminal prompt, not a command argument. Never commit operator credentials.
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
