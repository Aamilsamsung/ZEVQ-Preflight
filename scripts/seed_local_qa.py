"""Seed disposable local browser QA only; never use against a customer database."""
import json
import os
import secrets
import zipfile
from pathlib import Path
from sqlalchemy import select
from app.db import make_engine, factory, User, Organization, Membership
from app.security import hasher

if os.getenv('DATABASE_URL') or os.getenv('PREFLIGHT_MODE', 'development') != 'development':
    raise SystemExit('QA seeding requires the default disposable local database and development mode')

out = Path('artifacts'); out.mkdir(exist_ok=True)
password = secrets.token_urlsafe(32)
with factory(make_engine())() as db:
    user = db.scalar(select(User).where(User.email == 'qa@example.test'))
    if user:
        user.password_hash = hasher.hash(password)
    else:
        user = User(email='qa@example.test', password_hash=hasher.hash(password), verified=1)
        org = Organization(name='QA workspace')
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner'))
    db.commit()
credentials = out / 'qa-credentials.json'
credentials.write_text(json.dumps({'email': 'qa@example.test', 'password': password}))
credentials.chmod(0o600)
with zipfile.ZipFile(out / 'qa-source.zip', 'w') as archive:
    archive.writestr('app.py', 'def broken(\n')
print('Disposable local QA account and fixture created; credentials are not printed.')
