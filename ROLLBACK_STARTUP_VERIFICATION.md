# Verified previous-application startup remedy

Unmodified historical application `93ec40a16e0dbeeb7ea696de6291ceacb4060b73` does not contain migration 0006. Its normal automatic Alembic startup fails against that schema. Earlier imported-app compatibility tests did not establish historical artifact startup compatibility.

`scripts/prepare_rollback_bundle.py` archives that exact trusted application and retains the full current migration directory, Alembic configuration and locked dependencies. It writes a source manifest, refuses existing destinations, and does not connect to a database or deploy.

**Executed:** local regression 2 passed; dedicated CI run `41270626650`, job `124742481483`, success: 2 SQLite and 2 PostgreSQL16 tests passed. Tests reproduce old startup rejection, then verify prepared startup, actual previous-app login/organization/report reads and preserved original password hash, scan and schema 0006.

Source: `14ea82ee1226555c887ee4db62dfa870aec4d110`. Full relevant CI `41270626594` also passed 233 SQLite and 126 PostgreSQL tests, with 5 skips.

This is a tested prepared source bundle, not the historical Render artifact and not an actual hosted rollback. Review new-feature compatibility and authorized job handling before deployment. Never downgrade live schema or restore over staging to imitate application rollback. See OPERATIONS_RUNBOOK.md.
