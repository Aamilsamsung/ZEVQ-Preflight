"""Staging-boundary HTTPS tests; normal account sessions must work without Basic auth.

These exercise middleware/routes using a disposable database. Production startup's
PostgreSQL requirement is separately exercised by the hosted deployment and CI.
"""
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.db import Base, User, Organization, Membership, SessionRecord
from app.main import create_app
from app.security import hasher


@pytest.fixture
def staging(tmp_path, monkeypatch):
    monkeypatch.setenv('STAGING_PASSWORD', 'legacy-staging-secret-for-local-tests')
    monkeypatch.delenv('PUBLIC_ORIGIN', raising=False)
    app = create_app('sqlite:///' + str(tmp_path / 'staging.db'), mode='staging')
    Base.metadata.create_all(app.state.engine)
    with app.state.db() as db:
        user = User(email='owner@example.test', password_hash=hasher.hash('local-owner-test-password'), verified=1)
        org = Organization(name='Staging auth test')
        db.add_all([user, org]); db.flush()
        db.add(Membership(org_id=org.id, user_id=user.id, role='owner')); db.commit()
    client = TestClient(app, base_url='https://testserver', follow_redirects=False)
    yield app, client
    client.close(); app.state.engine.dispose()


def sign_in(client, headers=None):
    response = client.post('/api/auth/login', json={'email':'owner@example.test','password':'local-owner-test-password'}, headers=headers or {})
    assert response.status_code == 200
    return {'X-CSRF-Token':response.json()['csrf_token']}


def test_normal_staging_login_has_no_basic_auth_loop(staging):
    _, client = staging
    response = client.get('/app')
    assert response.status_code == 303 and response.headers['location'] == '/login'
    assert 'www-authenticate' not in response.headers
    assert client.get('/login').status_code == 200
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/api/auth/me').status_code == 401
    assert client.post('/api/auth/register', json={}).status_code == 403
    csrf = sign_in(client)
    assert client.get('/api/auth/me').status_code == 200
    assert client.get('/app').status_code == 200
    assert client.post('/api/orgs', json={'name':'No CSRF'}).status_code == 403
    assert client.post('/api/auth/logout', headers=csrf).status_code == 200
    assert client.get('/api/auth/me').status_code == 401
    assert client.get('/app').status_code == 303


def test_cached_wrong_basic_credentials_do_not_override_valid_session(staging):
    _, client = staging
    bad_header = {'Authorization':'Basic c3RhZ2luZzp3cm9uZw=='}
    assert client.get('/app', headers=bad_header).status_code == 303
    sign_in(client, bad_header)
    assert client.get('/api/auth/me', headers=bad_header).status_code == 200
    assert client.get('/app', headers=bad_header).status_code == 200


def test_staging_session_expiry_still_blocks_private_data(staging):
    app, client = staging
    sign_in(client)
    with app.state.db() as db:
        for session in db.scalars(select(SessionRecord)):
            session.expires = time.time() - 1
        db.commit()
    assert client.get('/api/auth/me').status_code == 401
    assert client.get('/app').status_code == 303


def test_unicode_basic_credentials_are_rejected_without_server_error(staging):
    import base64
    _,client=staging
    value=base64.b64encode('staging:é'.encode()).decode()
    assert client.get('/api/auth/me',headers={'Authorization':'Basic '+value}).status_code==401
