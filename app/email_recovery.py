"""Provisioned-account email verification/recovery. Delivery is opt-in and TLS-only.

Tokens are opaque bearer credentials: only SHA256 hashes are persisted; URLs use
fragments so tokens are never sent in request URLs or access logs. SMTP runs after
sending the generic HTTP response. Delivery failures are audited, never echoed.
"""
import os
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage
from urllib.parse import urlsplit
from fastapi import HTTPException
from sqlalchemy import select, delete, update
from .db import EmailToken, User, SessionRecord, Membership, Audit
from .security import digest, hasher

GENERIC = {'message': 'If an eligible provisioned account exists, an email will be sent. Check your inbox or contact support.'}
INVALID = 'This link is invalid, expired, or already used. Request a new email.'


def configuration():
    """No insecure SMTP fallback, redirects, caller-selected hosts or link origins."""
    if os.getenv('PREFLIGHT_EMAIL_ENABLED') != '1':
        return None
    origin = os.getenv('PUBLIC_ORIGIN', '')
    parsed = urlsplit(origin)
    sender = os.getenv('PREFLIGHT_SMTP_FROM', '')
    host = os.getenv('PREFLIGHT_SMTP_HOST', '')
    user = os.getenv('PREFLIGHT_SMTP_USERNAME', '')
    password = os.getenv('PREFLIGHT_SMTP_PASSWORD', '')
    port = os.getenv('PREFLIGHT_SMTP_PORT', '465')
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
        or parsed.path not in ('', '/') or parsed.query or parsed.fragment
        or not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+', sender)
        or not re.fullmatch(r'[a-zA-Z0-9.-]+', host) or not user or not password
        or port not in ('465', '587')):
        return None
    return {'origin': origin.rstrip('/'), 'sender': sender, 'host': host,
            'username': user, 'password': password, 'port': int(port)}


def audit(db, user_id, action):
    for org_id in db.scalars(select(Membership.org_id).where(Membership.user_id == user_id)):
        db.add(Audit(org_id=org_id, actor_id=user_id, action=action))


def deliver(config, recipient, purpose, token):
    """Only the transient message contains the raw token; no debug logging."""
    msg = EmailMessage()
    msg['From'], msg['To'] = config['sender'], recipient
    msg['Subject'] = 'ZEVQ Preflight: ' + ('reset your password' if purpose == 'reset' else 'verify your email')
    path = '/reset-password' if purpose == 'reset' else '/verify-email'
    msg.set_content('Use this single-use link within 15 minutes:\n\n' + config['origin'] + path + '#token=' + token
                    + '\n\nIf you did not request this email, ignore it. No password changes occur until you confirm. Never share this link.')
    context = ssl.create_default_context()
    if config['port'] == 465:
        with smtplib.SMTP_SSL(config['host'], 465, timeout=10, context=context) as smtp:
            smtp.login(config['username'], config['password']); smtp.send_message(msg)
    else:
        with smtplib.SMTP(config['host'], 587, timeout=10) as smtp:
            smtp.ehlo(); smtp.starttls(context=context); smtp.ehlo()
            smtp.login(config['username'], config['password']); smtp.send_message(msg)


def dispatch(factory, config, email, purpose):
    """After-response job; a lost process requires requesting a new link, not retrying secrets."""
    with factory() as db:
        user = db.scalar(select(User).where(User.email == email).with_for_update())
        if not user or (purpose == 'reset' and not user.verified) or (purpose == 'verify' and user.verified):
            return
        token = secrets.token_urlsafe(48)
        row = EmailToken(token_hash=digest(token), user_id=user.id, purpose=purpose,
                         expires=time.time() + 900, consumed_at=None)
        # Invalidate earlier outstanding links, but retain hashes/audit evidence.
        db.execute(update(EmailToken).where(EmailToken.user_id == user.id, EmailToken.purpose == purpose,
                   EmailToken.consumed_at.is_(None)).values(consumed_at=time.time()))
        db.add(row); audit(db, user.id, 'account.email_' + purpose + '_requested'); db.commit()
        token_hash, user_id = row.token_hash, user.id
    try:
        deliver(config, email, purpose, token)
        action = 'account.email_' + purpose + '_submitted'
    except Exception:
        # Includes provider errors; never persist exception text or recipient/token.
        action = 'account.email_' + purpose + '_failed'
        with factory() as db:
            db.execute(update(EmailToken).where(EmailToken.token_hash == token_hash).values(consumed_at=time.time()))
            audit(db, user_id, action); db.commit()
        return
    with factory() as db:
        audit(db, user_id, action); db.commit()


def consume(factory, token, purpose, password=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{64}', token):
        raise HTTPException(400, INVALID)
    hashed = digest(token)
    # Find identity, then serialize every token mutation for that user, including
    # parallel resets, resends and password changes. Never lock token before user.
    with factory() as db:
        identity = db.scalar(select(EmailToken.user_id).where(EmailToken.token_hash == hashed))
        if not identity:
            raise HTTPException(400, INVALID)
        user = db.scalar(select(User).where(User.id == identity).with_for_update())
        row = db.scalar(select(EmailToken).where(EmailToken.token_hash == hashed).with_for_update())
        now = time.time()
        if not user or not row or row.purpose != purpose or row.expires <= now or row.consumed_at is not None:
            raise HTTPException(400, INVALID)
        if purpose == 'reset':
            if not user.verified:
                raise HTTPException(400, INVALID)
            user.password_hash = hasher.hash(password)
            db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id))
        else:
            user.verified = 1
        # All links for this identity are invalidated atomically with the change.
        db.execute(update(EmailToken).where(EmailToken.user_id == user.id, EmailToken.consumed_at.is_(None)).values(consumed_at=now))
        audit(db, user.id, 'account.password_reset_email' if purpose == 'reset' else 'account.email_verified')
        db.commit()
