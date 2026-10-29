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


def constant_equal(left, right):
    # HTTP values may contain non-ASCII text; compare_digest(str,str) raises for
    # these inputs. Compare bytes so malformed credentials fail closed.
    return secrets.compare_digest(left.encode('utf-8'), right.encode('utf-8'))


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


def authenticated(request):
    """One database-backed identity snapshot per request; never cached across requests."""
    cached=getattr(request.state,'preflight_identity',None)
    if cached is not None:
        if cached[1].expires < time.time():raise HTTPException(401,'Sign in required')
        return cached
    token=request.cookies.get('preflight_session','')
    if not token:raise HTTPException(401,'Sign in required')
    with request.app.state.db() as db:
        row=db.execute(select(User,SessionRecord).join(SessionRecord,SessionRecord.user_id==User.id).where(
            SessionRecord.token_hash==digest(token),SessionRecord.expires>time.time(),User.verified==1)).first()
        if row is None:raise HTTPException(401,'Sign in required')
        identity=(row[0],row[1])
    request.state.preflight_identity=identity
    return identity


def principal(request: Request):
    user,session=authenticated(request)
    # Authentication reuse must never bypass the endpoint's mutation checks.
    if request.method not in ('GET','HEAD','OPTIONS'):
        supplied=request.headers.get('X-CSRF-Token','')
        if not constant_equal(supplied,session.csrf):raise HTTPException(403,'Invalid CSRF token')
    return user,session


def member(request, org_id, roles=None):
    user, session = principal(request)
    with request.app.state.db() as db:
        membership = db.get(Membership, (org_id, user.id))
        if not membership:
            raise HTTPException(404, 'Organization not found')
        if roles and membership.role not in roles:
            raise HTTPException(403, 'Role does not permit this action')
    return user, session


def has_active_session(request):
    """The staging boundary shares identity only within this request; CSRF/RBAC remain enforced."""
    try:
        authenticated(request)
        return True
    except HTTPException as exc:
        if exc.status_code==401:return False
        raise
