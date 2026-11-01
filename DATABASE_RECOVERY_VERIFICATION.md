# Database recovery verification

**Status: partial — actual restored-application acceptance remains blocked.**

- Live URL: https://zevq-preflight-staging.onrender.com
- Deployed application: `e612f03dda7cd10d139ec4b95472ce978d5bf14c`
- Render deployment: `dep-dbj34r7b9u1s73cu1qqg` — live
- Render service: `srv-dbgr4v0n74is73d798e0`, Free, automatic deployment off
- Configured release branch: `implementation/secure-preflight`
- Active development branch: `implementation/public-onboarding-20261029`
- Neon project: `dawn-bonus-77001287`; live migration: `0006`
- Report commit: the Git commit containing this file.

## Executed

Migration 0006 was rehearsed using exact generated PostgreSQL DDL on isolated branch `br-orange-boat-b3dljf23` (`migration-0006-validation-20261031`), copied from staging at parent LSN `0/1F36F00`. Original counts and expected constraints were verified. The live rollout then applied 0006 and preserved the pre-QA baseline: 4 users, 28 scans, 4 organizations, 3 reviews and 9 sessions. Later labeled synthetic QA additions are separate from that preservation evidence.

Existing CI passed synthetic PostgreSQL backup/restore, row/report/review checks, tenant isolation and previous-application read compatibility. Seven new recovery-runner safety tests passed, including original-row fingerprint preservation and detection of edits to original data.

The prepared hosted runner allows only `ep-dark-king-b3w2usjz.c-4.ap-southeast-1.aws.neon.tech/neondb`, enforces verified TLS, checks the current source head and never imports destructive database test fixtures. Original business rows and historical session records must remain unchanged. Expiring rate-limit buckets are explicitly excluded; historical plaintext session tokens are unavailable, so new synthetic sessions are tested separately.

## Not executed

Run 41231594461 stopped at the missing `PREFLIGHT_RECOVERY_DATABASE_URL` secret check before a database connection. Do not call this a successful restored-application run, live restore, or complete disaster recovery.

After secure owner setup, create a fresh `RECOVERY_RUN_REQUEST.md` at the current guarded branch head. Do not rerun an old job after newer commits: the source-head guard intentionally rejects that situation. Inspect startup, login/session, worker, report/export, isolation and original-row fingerprint results.

## Application rollback correction

A historical 93ec40a artifact lacks migration 0006 and its automatic Alembic startup fails against that schema. `scripts/prepare_rollback_bundle.py` retains the trusted previous application with the full current migration history and locked dependencies. Dedicated CI 41270626650 verified startup, login/report reads and preserved records on both SQLite and PostgreSQL16.

Use a reviewed prepared source bundle if rollback becomes necessary. Do not blindly reuse the historical Render artifact, downgrade the live database, or restore over staging. Actual hosted rollback has not been performed; RPO/RTO and provider backup-erasure guarantees are not established.
