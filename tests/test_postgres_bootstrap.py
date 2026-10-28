"""Dedicated CI PostgreSQL only; never configure TEST_DATABASE_URL for customer data."""
import os
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit
import psycopg
import pytest
from app.db import Base, make_engine


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'), reason='Dedicated PostgreSQL CI database required')
def test_runtime_role_can_use_application_tables_without_admin_privileges():
    direct = os.environ['TEST_DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')
    engine = make_engine(direct)
    Base.metadata.create_all(engine)
    engine.dispose()
    env = os.environ.copy()
    env.update(DATABASE_URL_UNPOOLED=direct, PREFLIGHT_BOOTSTRAP_EMAIL='bootstrap-ci@example.test', PREFLIGHT_BOOTSTRAP_PASSWORD='ci-bootstrap-password-not-a-real-secret', PREFLIGHT_RUNTIME_PASSWORD='ci-runtime-password-not-a-real-secret')
    for _ in range(2):
        subprocess.run([sys.executable, '-m', 'app.bootstrap'], env=env, check=True, capture_output=True)
    parsed = urlsplit(direct)
    runtime = urlunsplit((parsed.scheme, 'preflight_runtime:ci-runtime-password-not-a-real-secret@' + parsed.netloc.split('@', 1)[1], parsed.path, parsed.query, ''))
    with psycopg.connect(runtime) as db:
        assert db.execute('SELECT COUNT(*) FROM organizations').fetchone()[0] >= 1
        flags = db.execute('SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
        assert flags == (False, False, False, False)
        assert not db.execute("SELECT has_schema_privilege(current_user, 'public', 'CREATE')").fetchone()[0]
        assert not db.execute("SELECT has_table_privilege(current_user, 'public.alembic_version', 'UPDATE')").fetchone()[0]
