"""Closed-account credential changes; no email delivery or public recovery claims."""
import re
from sqlalchemy import select, delete
from .db import User, Membership, SessionRecord, Audit, EmailToken
from .security import hasher


def validate_password(password):
    if not 14 <= len(password) <= 256:
        raise ValueError('Password must be 14–256 characters')


def reset_password(db_factory, email, password, *, identity_verified=False, reference=''):
    """Trusted operator only. Never called by an HTTP recovery endpoint."""
    if not identity_verified or not re.fullmatch(r'[A-Za-z0-9._-]{3,64}', reference):
        raise ValueError('Verified identity and a non-secret support reference are required')
    validate_password(password)
    with db_factory() as db:
        user = db.scalar(select(User).where(User.email == email.strip().lower()).with_for_update())
        if not user:
            raise ValueError('Account not found')
        db.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
        user.password_hash = hasher.hash(password)
        db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id))
        for org in db.scalars(select(Membership.org_id).where(Membership.user_id == user.id)):
            db.add(Audit(org_id=org, actor_id='operator', action='account.password_reset:' + reference))
        db.commit()
