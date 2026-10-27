"""Opaque revocable sessions; passwords never leave server-side Argon2 hashing."""
import hashlib
import secrets
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException, Request
from sqlalchemy import select, delete, update
from sqlalchemy.exc import IntegrityError
from .db import SessionRecord, User, Membership, RateBucket

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_ok(encoded, password):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def limit(factory, key, maximum, seconds):
    """Database counter shared across processes, no per-process limiter bypass."""
    now = time.time()
    bucket = digest(key + ':' + str(int(now // seconds)))
    with factory() as db:
        db.execute(delete(RateBucket).where(RateBucket.expires < now))
        try:
            with db.begin_nested():
                db.add(RateBucket(key=bucket, count=0, expires=now + seconds * 2))
                db.flush()
        except IntegrityError:
            pass
        value = db.execute(update(RateBucket).where(RateBucket.key == bucket).values(count=RateBucket.count + 1).returning(RateBucket.count)).scalar_one()
        db.commit()
    if value > maximum:
        raise HTTPException(429, 'Rate limit reached. Try again later.', headers={'Retry-After': str(seconds)})


def principal(request: Request):
    token = request.cookies.get('preflight_session', '')
    with request.app.state.db() as db:
        session = db.get(SessionRecord, digest(token)) if token else None
        if not session or session.expires < time.time():
            raise HTTPException(401, 'Sign in required')
        user = db.get(User, session.user_id)
        if not user or not user.verified:
            raise HTTPException(401, 'Verified account required')
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            supplied = request.headers.get('X-CSRF-Token', '')
            if not secrets.compare_digest(supplied, session.csrf):
                raise HTTPException(403, 'Invalid CSRF token')
        return user, session


def member(request, org_id, roles=None):
    user, session = principal(request)
    with request.app.state.db() as db:
        membership = db.get(Membership, (org_id, user.id))
        if not membership:
            raise HTTPException(404, 'Organization not found')
        if roles and membership.role not in roles:
            raise HTTPException(403, 'Role does not permit this action')
    return user, session
