"""Seed disposable local browser QA only; never use against a customer database."""
import json
import os
import secrets
import zipfile
from pathlib import Path
from sqlalchemy import select
from app.db import make_engine, factory, User, Organization, Membership, Scan
from app.security import hasher
from app.analyzer import analyze

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
viewer_password = secrets.token_urlsafe(32)
with factory(make_engine())() as db:
    owner = db.scalar(select(User).where(User.email == 'qa@example.test'))
    org_id = db.scalar(select(Membership.org_id).where(Membership.user_id == owner.id, Membership.role == 'owner'))
    viewer = db.scalar(select(User).where(User.email == 'qa-viewer@example.test'))
    if not viewer:
        viewer = User(email='qa-viewer@example.test', password_hash=hasher.hash(viewer_password), verified=1)
        db.add(viewer); db.flush()
    else:
        viewer.password_hash = hasher.hash(viewer_password)
    membership = db.get(Membership, (org_id, viewer.id))
    if not membership:
        db.add(Membership(org_id=org_id, user_id=viewer.id, role='viewer'))
    else:
        membership.role = 'viewer'
    scan = Scan(org_id=org_id, status='completed', result=json.dumps(analyze({'app.py':'def broken(\n'})))
    db.add(scan); db.commit()
    (out / 'qa-review-scan.json').write_text(json.dumps({'scan_id':scan.id}))
    clean = Scan(org_id=org_id, status='completed', result=json.dumps(analyze({'app.py':'def valid():\n    return True\n'})))
    db.add(clean); db.commit()
    (out / 'qa-comparison.json').write_text(json.dumps({'baseline_id':scan.id,'proposed_id':clean.id}))
viewer_credentials = out / 'qa-viewer-credentials.json'
viewer_credentials.write_text(json.dumps({'email':'qa-viewer@example.test','password':viewer_password}))
viewer_credentials.chmod(0o600)
credentials = out / 'qa-credentials.json'
credentials.write_text(json.dumps({'email': 'qa@example.test', 'password': password}))
credentials.chmod(0o600)
with zipfile.ZipFile(out / 'qa-source.zip', 'w') as archive:
    archive.writestr('app.py', 'def broken(\n')
print('Disposable local QA account and fixture created; credentials are not printed.')
