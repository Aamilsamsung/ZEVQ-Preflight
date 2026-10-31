"""Exercise the free-instance supervisor through real HTTP and child processes."""
import json
import os
import socket
import subprocess
import sys
import time

import httpx
from app.db import make_engine, factory, User, Organization, Membership
from app.security import hasher


def test_free_instance_processes_a_durable_contract_job(tmp_path):
    env = os.environ.copy()
    env['DATABASE_URL'] = 'sqlite:///' + str(tmp_path / 'free-instance.db')
    env['PREFLIGHT_MODE'] = 'development'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); env['PORT'] = str(sock.getsockname()[1])
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], env=env, check=True, capture_output=True)
    engine = make_engine(env['DATABASE_URL'])
    with factory(engine)() as db:
        user = User(email='free@example.test', password_hash=hasher.hash('local-test-password'), verified=1)
        org = Organization(name='Free instance test')
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner')); db.commit(); org_id = org.id
    engine.dispose()
    process = subprocess.Popen([sys.executable, '-m', 'app.serve'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url='http://127.0.0.1:' + env['PORT'], trust_env=False, timeout=5) as client:
            deadline = time.monotonic() + 20
            while True:
                try:
                    if client.get('/health').status_code == 200: break
                except httpx.TransportError: pass
                assert process.poll() is None, 'supervisor exited before readiness'
                assert time.monotonic() < deadline, 'web process did not become ready'
                time.sleep(0.1)
            response = client.post('/api/auth/login', json={'email':'free@example.test', 'password':'local-test-password'})
            assert response.status_code == 200
            headers = {'X-CSRF-Token': response.json()['csrf_token']}
            baseline = {'openapi':'3.0.3','paths':{'/orders':{'get':{'responses':{'200':{'description':'OK'}}}}}}
            proposed = {'openapi':'3.0.3','paths':{}}
            response = client.post(f'/api/orgs/{org_id}/contracts', json={'baseline':baseline,'proposed':proposed}, headers=headers)
            assert response.status_code == 202
            scan_id = response.json()['id']
            deadline = time.monotonic() + 15
            while True:
                scan = client.get(f'/api/orgs/{org_id}/scans/{scan_id}').json()
                if scan['status'] in ('completed', 'failed'): break
                assert time.monotonic() < deadline, 'on-demand worker did not process the wake-up'
                time.sleep(0.2)
            assert scan['status'] == 'completed', scan.get('error')
            assert scan['result']['findings'][0]['rule'] == 'OAS.ENDPOINT_REMOVED'
            assert scan['result']['simulation']['status'] == 'not-executed'
            assert process.poll() is None
    finally:
        process.terminate()
        process.wait(timeout=15)
    assert process.returncode == 0


def test_supervisor_fails_if_a_service_exits():
    code = '''import sys
from app.serve import supervise
raise SystemExit(supervise([[sys.executable,'-c','import time; time.sleep(60)'], [sys.executable,'-c','raise SystemExit(7)']]))
'''
    result = subprocess.run([sys.executable, '-c', code], timeout=15, capture_output=True)
    assert result.returncode == 1
