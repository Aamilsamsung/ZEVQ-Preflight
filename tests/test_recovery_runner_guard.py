import pytest
from scripts.hosted_recovery_acceptance import snapshot_url, SNAPSHOT_HOST


def test_only_explicit_snapshot_endpoint_allowed_and_tls_verified():
    value = snapshot_url(f'postgresql://fixture:fixture@{SNAPSHOT_HOST}/neondb?sslmode=require')
    assert 'sslmode=verify-full' in value


@pytest.mark.parametrize('value', [
    'postgresql://fixture:fixture@ep-lingering-glade-b3vgftj2.c-4.ap-southeast-1.aws.neon.tech/neondb',
    'postgresql://fixture:fixture@localhost/neondb',
    f'postgresql://fixture:fixture@{SNAPSHOT_HOST}/another',
    f'postgresql://{SNAPSHOT_HOST}/neondb',
    '',
])
def test_live_unknown_or_missing_endpoint_rejected_before_connect(value):
    with pytest.raises(ValueError):
        snapshot_url(value)


def test_original_rows_remain_verifiable_after_synthetic_additions(tmp_path):
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session
    from app.db import Base, User
    from scripts.hosted_recovery_acceptance import fingerprints
    engine = create_engine('sqlite:///' + str(tmp_path / 'fingerprint.db'))
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE alembic_version(version_num VARCHAR(32) PRIMARY KEY)'))
        connection.execute(text("INSERT INTO alembic_version VALUES('0006')"))
    with Session(engine) as db:
        original = User(email='original@example.test', password_hash='fixture-only', verified=1)
        db.add(original); db.commit(); original_id = original.id
    with engine.connect() as connection:
        keys, before = fingerprints(connection)
    with Session(engine) as db:
        db.add(User(email='new-synthetic@example.test', password_hash='fixture-only', verified=1)); db.commit()
    with engine.connect() as connection:
        _, preserved = fingerprints(connection, keys)
    assert preserved == before
    with Session(engine) as db:
        db.get(User, original_id).verified = 0; db.commit()
    with engine.connect() as connection:
        _, changed = fingerprints(connection, keys)
    assert changed['users'] != before['users']
    engine.dispose()
