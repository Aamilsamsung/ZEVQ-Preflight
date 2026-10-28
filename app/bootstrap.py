"""Explicit closed-staging provisioning; never an HTTP registration endpoint.

The operator supplies an attested email and random password through host secrets.
Existing accounts/passwords are never reset by a restart.
"""
import os
from sqlalchemy import select
from psycopg import sql
from .db import make_engine, factory, User, Organization, Membership
from .security import hasher


def provision_account(db_factory, email, password, organization='ZEVQ Labs'):
    if not email or '@' not in email or len(password) < 24:
        raise ValueError('A staging account email and strong provisioning password are required')
    with db_factory() as db:
        if db.scalar(select(User).where(User.email == email.lower().strip())):
            return False
        user = User(email=email.lower().strip(), password_hash=hasher.hash(password), verified=1)
        org = Organization(name=organization)
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner')); db.commit()
    return True


def main():
    direct = os.getenv('DATABASE_URL_UNPOOLED')
    email = os.getenv('PREFLIGHT_BOOTSTRAP_EMAIL')
    password = os.getenv('PREFLIGHT_BOOTSTRAP_PASSWORD', '')
    runtime_password = os.getenv('PREFLIGHT_RUNTIME_PASSWORD', '')
    if not direct or not email or len(password) < 24 or len(runtime_password) < 24:
        raise RuntimeError('Explicit staging provisioning secrets are incomplete')
    engine = make_engine(direct)
    try:
        if engine.dialect.name != 'postgresql':
            raise RuntimeError('Hosted provisioning requires PostgreSQL')
        with engine.begin() as conn:
            driver = conn.connection.driver_connection
            exists = driver.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', ('preflight_runtime',)).fetchone()
            if not exists:
                driver.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS').format(sql.Identifier('preflight_runtime'), sql.Literal(runtime_password)))
            driver.execute('GRANT USAGE ON SCHEMA public TO preflight_runtime')
            driver.execute('GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO preflight_runtime')
            driver.execute('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO preflight_runtime')
            driver.execute('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO preflight_runtime')
            driver.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            if driver.execute("SELECT to_regclass('public.alembic_version')").fetchone()[0]:
                driver.execute('REVOKE ALL ON TABLE public.alembic_version FROM preflight_runtime')
        created = provision_account(factory(engine), email, password)
        print('Closed-staging runtime role ready; account ' + ('provisioned.' if created else 'already exists; password unchanged.'))
    finally:
        engine.dispose()

if __name__ == '__main__':
    main()
