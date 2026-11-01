# Historical artifact startup gap and prepared rollback bundle

Confirmed on a disposable local SQLite database at schema0006:unmodified application93ec40a runs Alembic startup but lacks revision0006,so upgradehead fails. Existing syntheticCI tests imported older application code against a restored DB;they did not prove its historical start command could resolve the newer revision. Do not use one-click rollback to that old Render artifact as a proven recovery procedure.

Prepared fix:scripts/prepare_rollback_bundle.py archives the exact trusted application93ec40a,retains the full current migration directory plus locked dependencies,and writes a source manifest. It never connects to a DB,downgrades,deletes customerdata or deploys. Existing destination paths are refused. Review and deploy this prepared source through the normal guarded release process when an application rollback is actually required. Its source bundle differs from a historical Render build.

Local regression2passed:historicalstartup rejected0006 as expected;preparedbundle Alembicstartup succeeds;the actual93ec40a application logs in and reads existing organization/report;passwordhash,scan and schema0006 preserved. Second test confirms existing destinations cannot be overwritten.

A dedicated CI workflow now tests the same startup path on both disposableSQLite and PostgreSQL16. PostgreSQL result pending until that run completes. This is prepared rollback startup verification,not an actual hosted rollout/rollback. Current staging application/deployment/database are unchanged. Private jobs must be drained/cancelled under approved application procedures before a rollback;older behavior must not be represented as supporting new private/onboarding features.
