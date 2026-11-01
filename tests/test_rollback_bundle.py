import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from sqlalchemy import create_engine, text
from scripts.prepare_rollback_bundle import prepare, PREVIOUS_APP

ROOT = Path(__file__).resolve().parents[1]


def test_prepared_previous_application_starts_on_current_schema_without_data_loss(tmp_path):
    url = os.getenv('ROLLBACK_TEST_DATABASE_URL') or 'sqlite:///' + str(tmp_path / 'recovery.db')
    if os.getenv('ROLLBACK_TEST_DATABASE_URL'):
        parsed = urlsplit(url)
        assert parsed.hostname in ('localhost', '127.0.0.1') and parsed.path == '/preflight_rollback'
        assert parsed.scheme == 'postgresql+psycopg' and not parsed.query and not parsed.fragment
    env = {**os.environ, 'DATABASE_URL': url, 'DATABASE_URL_UNPOOLED': url}
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=ROOT, env=env, check=True, capture_output=True)
    from app.db import User, Organization, Membership, Scan
    from sqlalchemy.orm import Session
    from app.security import hasher
    engine = create_engine(url)
    password = 'synthetic-rollback-fixture-password'
    with Session(engine) as db:
        user = User(email='qa-rollback@example.test', password_hash=hasher.hash(password), verified=1)
        org = Organization(name='Disposable rollback fixture')
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner'))
        scan = Scan(org_id=org.id, status='completed', result=json.dumps({'findings': [], 'simulation': {'status': 'not-executed'}}))
        db.add(scan); db.commit(); user_id, org_id, scan_id = user.id, org.id, scan.id
        original_hash = user.password_hash
    historical = tmp_path / 'historical'; historical.mkdir()
    archive = subprocess.check_output(['git', '-C', str(ROOT), 'archive', '--format=tar', PREVIOUS_APP])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(historical, filter='data')
    failure = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=historical, env=env, capture_output=True, text=True)
    assert failure.returncode != 0 and '0006' in failure.stdout + failure.stderr
    bundle = tmp_path / 'prepared'
    manifest = prepare(ROOT, bundle)
    assert manifest['database_or_deployment_changes'] is False
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=bundle, env=env, check=True, capture_output=True)
    proof = '''
import sys
from pathlib import Path
from fastapi.testclient import TestClient
import app.main
assert Path(app.main.__file__).resolve().is_relative_to(Path.cwd())
application=app.main.create_app(sys.argv[1],mode='development')
with TestClient(application) as client:
 r=client.post('/api/auth/login',json={'email':'qa-rollback@example.test','password':'synthetic-rollback-fixture-password'})
 assert r.status_code==200
 assert client.get('/api/auth/me').json()['organizations'][0]['id']==sys.argv[2]
 report=client.get('/api/orgs/'+sys.argv[2]+'/scans/'+sys.argv[3]+'/report')
 assert report.status_code==200 and report.json()['status']=='completed'
'''
    subprocess.run([sys.executable, '-c', proof, url, org_id, scan_id], cwd=bundle, env=env, check=True, capture_output=True)
    with Session(engine) as db:
        assert db.get(User, user_id).password_hash == original_hash
        assert db.get(Scan, scan_id).status == 'completed'
        assert db.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0006'
    engine.dispose()


def test_builder_refuses_to_overwrite_existing_work(tmp_path):
    with pytest.raises(FileExistsError):
        prepare(ROOT, tmp_path)
