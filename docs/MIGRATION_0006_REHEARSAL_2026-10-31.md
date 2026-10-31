# Isolated Neon migration0006 rehearsal

Date:31October2026. Project dawn-bonus-77001287 confirmed free_v3.
Parent staging br-solitary-hall-b3y011t5 at schema0005. Isolated snapshot br-orange-boat-b3dljf23,parentLSN0/1F36F00,compute ep-dark-king-b3w2usjz fixed0.25CU/immediate suspend.

Executed the upgrade() function in migrations/versions/0006_public_onboarding.py through Alembic Operations with PostgreSQL offline dialect to generate exact additive DDL. Applied those statements and version update as one transaction through authenticated Neon SQL on the isolated branch. No live data changed.

Result: version0006. users4,scans28,organizations4,finding_reviews3,sessions9 unchanged. All4 existing accounts retain registration_pending0. All28 historical scans retain NULL created_by. Verified primary key account_events_pkey and foreign keys account_events_user_id_fkey/fk_scans_created_by.

The existing candidate CI40883465251 also passed actual PostgreSQL Alembic upgrade/downgrade/upgrade,API tests,synthetic backup/restore,previous-app compatibility and browser journeys. Fresh local recovery suite224pass/5skip.

Limitations: this runner cannot resolve the Neon endpoint,so a direct Alembic/application run against the hosted snapshot could not be performed here. The hosted rehearsal is exact generated-DDL execution and data/constraint verification,not claimed as a hosted restored-app journey. Snapshot is retained;do not reset staging to it or downgrade live tables.

Safe release: deploy candidate with public registration/access flags still disabled. Startup app.serve runs Alembic upgrade head and bootstrap refreshes runtime table privileges. Verify schema0006,unchanged records and deployed commit. Application rollback must preserve schema0006;previous application compatibility was tested in CI. No schema downgrade as rollback.
