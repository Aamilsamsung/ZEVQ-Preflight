from sqlalchemy import select, func
from app.db import Base, make_engine, factory, User, Membership
from app.bootstrap import provision_account
from app.security import password_ok


def test_staging_provisioning_is_idempotent_and_never_resets_password(tmp_path):
    engine = make_engine('sqlite:///' + str(tmp_path / 'bootstrap.db'))
    Base.metadata.create_all(engine)
    db_factory = factory(engine)
    first = 'first-local-test-password-123456'
    second = 'different-test-password-1234567'
    assert provision_account(db_factory, 'owner@example.test', first)
    assert not provision_account(db_factory, 'OWNER@example.test', second)
    with db_factory() as db:
        user = db.scalar(select(User))
        assert password_ok(user.password_hash, first)
        assert not password_ok(user.password_hash, second)
        assert db.scalar(select(func.count()).select_from(Membership)) == 1
        assert db.scalar(select(Membership)).role == 'owner'
    engine.dispose()
