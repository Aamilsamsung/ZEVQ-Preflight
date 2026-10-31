"""Gated public onboarding. No account receives access before mailbox proof."""
import os
import re
import secrets
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .db import User, AccountEvent
from .security import hasher
from .email_recovery import configuration

LEGAL_VERSION='2026-10-29'
GENERIC={'message':'If this address is eligible, a verification email will be sent. Follow it to choose your password, then sign in.'}


def available():
    return (os.getenv('PREFLIGHT_REGISTRATION_ENABLED')=='1'
            and os.getenv('PREFLIGHT_LEGAL_APPROVED_VERSION')==LEGAL_VERSION
            and configuration() is not None)


def normalize_email(value):
    value=value.strip().lower()
    if len(value)>254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}",value):
        raise ValueError('Enter a valid email address. Internationalized email addresses are not supported in this release.')
    local,domain=value.rsplit('@',1)
    if len(local)>64 or local.startswith('.') or local.endswith('.') or '..' in local or any(not part or len(part)>63 or part.startswith('-') or part.endswith('-') for part in domain.split('.')):
        raise ValueError('Enter a valid email address.')
    return value


def provision(factory,email):
    """Never replace an existing account/password. Mail confirmation sets the password.

    Hash a random unusable credential even for duplicates to keep this operation's
    expensive work independent of account existence. Generic HTTP responses remain
    necessary; complete timing indistinguishability is not claimed.
    """
    encoded=hasher.hash(secrets.token_urlsafe(48))
    with factory() as db:
        user=db.scalar(select(User).where(User.email==email))
        if user:return
        try:
            with db.begin_nested():
                user=User(email=email,password_hash=encoded,verified=0,registration_pending=1)
                db.add(user);db.flush()
                db.add(AccountEvent(user_id=user.id,action='registration.terms_accepted:'+LEGAL_VERSION))
            db.commit()
        except IntegrityError:
            # A concurrent signup for the same normalized mailbox won. It must
            # not overwrite that account or expose its existence.
            db.rollback()
