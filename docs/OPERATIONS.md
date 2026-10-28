# Operator guide

## Architecture and deployment status

FastAPI serves a vanilla JavaScript/CSS frontend and tenant-scoped APIs. SQLAlchemy/Alembic manages PostgreSQL records. A separately launched Python worker claims durable jobs using a row lock/conditional update and runs the static analyzer in a bounded child process. Customer code is never imported or executed. This process separation is not a sandbox suitable for running customer tests.

There is currently **no deployed Preflight service or live application URL**. Render rejected a dedicated free database: `cannot have more than one active free tier database`. No other project's database was reused, and no paid resources were created.

Proposed Render configuration: Singapore, free web service, `0.5c-512mb` static worker, dedicated PostgreSQL 16 on `0.1c-256mb`. The public schema validator accepted the Blueprint. Render CLI/platform deployment validation and live verification remain pending.

The pricing page retrieved on 27 October 2026 listed $7/month for the worker and $6/month for database compute: about **$13/month compute**, plus applicable storage, usage and taxes. Free web hosting has platform limits and sleep behavior. This is an estimate for the proposed configuration, not a bill or a deployed configuration. Source: https://render.com/pricing . A paid $7 web service would bring compute to approximately $20/month. Reconfirm current pricing before purchase.

## Restricted deployment procedure

1. Obtain approval for the proposed paid database and worker, or supply a dedicated PostgreSQL/worker hosting alternative.
2. Ensure the exact tested branch/commit is in GitHub. Do not point deployment at the older main branch.
3. Create the dedicated database, API/web service and static worker from the reviewed Blueprint. No resources named for other products should be changed.
4. Supply `PUBLIC_ORIGIN` as the exact HTTPS staging origin. Keep `PREFLIGHT_MODE=staging` on both services. Store the generated `STAGING_PASSWORD` in the host secret store.
5. The web start command applies `alembic upgrade head` before starting Uvicorn. The worker tolerates database unavailability and retries polling. A coordinated maintenance window is necessary for future incompatible schema changes.
6. Configure platform health checks at `/health`. This is liveness only. Authenticated `/api/ready` checks database reachability; a worker heartbeat/alert is not yet implemented.
7. Use HTTP Basic username `staging` and the generated password to access staging. Account sign-in remains a second separate requirement. Public registration remains disabled server-side.
8. From a trusted operator shell with the staging database environment, run `python -m app.manage create-user --email YOUR_VERIFIED_EMAIL --organization 'ZEVQ Labs' --identity-verified`. Password input uses a terminal prompt, not a command argument. Never commit operator credentials.
9. Verify unauthorized access is rejected, sessions persist across refresh, source comparisons finish, private reports require membership, and the deployed SHA matches the reviewed commit.
10. Run browser checks on the deployed URL. Do not approve public launch from local checks alone.

The Blueprint uses manual auto-deploy settings. Applying the Blueprint is an infrastructure action, not a public launch approval.

## Worker behavior and limits

- One job per worker process. PostgreSQL locking supports multiple worker instances; concurrency has not been load-tested.
- Per organization: three pending jobs, 20 scans per rolling day, 20 connected repositories.
- Compressed archive limit 8 MB, selected UTF-8 sources at most 400 files, at most 300 KB per file, extracted selected content at most 8 MB.
- HTTP bodies are bounded, including chunked requests. These are application limits, not full infrastructure DDoS protection.
- Static job timeout 120 seconds; calculation timeout 90 seconds; Linux child CPU limit 60 seconds and address-space limit 768 MB. Hosting may enforce a lower memory cap.
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
