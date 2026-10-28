import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_api import env, login
from app.accounts import reset_password
from app.db import Audit


def test_password_change_revokes_sessions_and_requires_reauth(env):
    app,c,_=env;h=login(c)
    other=TestClient(app);login(other)
    payload={'current_password':'correct-password','new_password':'new-strong-password-123'}
    assert c.post('/api/auth/password',json=payload).status_code==403
    assert c.post('/api/auth/password',json={**payload,'current_password':'wrong'},headers=h).status_code==403
    assert other.get('/api/auth/me').status_code==200
    assert c.post('/api/auth/password',json=payload,headers=h).json()['sign_in_required']
    assert other.get('/api/auth/me').status_code==401
    assert c.get('/api/auth/me').status_code==401
    assert c.post('/api/auth/login',json={'email':'owner@example.test','password':'correct-password'}).status_code==401
    assert c.post('/api/auth/login',json={'email':'owner@example.test','password':payload['new_password']}).status_code==200


def test_operator_reset_requires_attestation_and_revokes_sessions(env):
    app,c,_=env;login(c)
    with pytest.raises(ValueError):reset_password(app.state.db,'owner@example.test','new-secure-password-123',reference='ticket-123')
    assert c.get('/api/auth/me').status_code==200
    reset_password(app.state.db,'owner@example.test','new-secure-password-123',identity_verified=True,reference='ticket-123')
    assert c.get('/api/auth/me').status_code==401
    assert c.post('/api/auth/login',json={'email':'owner@example.test','password':'new-secure-password-123'}).status_code==200
    with app.state.db() as db:
        assert db.scalar(select(Audit).where(Audit.action=='account.password_reset:ticket-123'))


def test_owner_can_change_and_revoke_membership(env):
    app,c,(org,*_)=env;h=login(c)
    viewer=TestClient(app);vh=login(viewer,'viewer@example.test');uid=viewer.get('/api/auth/me').json()['id']
    assert viewer.post(f'/api/orgs/{org}/repos',json={'full_name':'qa/one'},headers=vh).status_code==403
    assert c.patch(f'/api/orgs/{org}/members/{uid}',json={'role':'developer'},headers=h).status_code==200
    assert viewer.post(f'/api/orgs/{org}/repos',json={'full_name':'qa/one'},headers=vh).status_code==201
    assert c.patch(f'/api/orgs/{org}/members/{uid}',json={'role':'viewer'},headers=h).status_code==200
    assert viewer.post(f'/api/orgs/{org}/repos',json={'full_name':'qa/two'},headers=vh).status_code==403
    assert c.delete(f'/api/orgs/{org}/members/{uid}',headers=h).status_code==200
    assert viewer.get(f'/api/orgs/{org}/repos').status_code==404


def test_role_changes_cannot_escalate_or_cross_tenants(env):
    app,c,(org,other,owner_id,other_id)=env;h=login(c)
    viewer=TestClient(app);vh=login(viewer,'viewer@example.test');viewer_id=viewer.get('/api/auth/me').json()['id']
    assert viewer.patch(f'/api/orgs/{org}/members/{viewer_id}',json={'role':'administrator'},headers=vh).status_code==403
    assert c.patch(f'/api/orgs/{other}/members/{other_id}',json={'role':'viewer'},headers=h).status_code==404
    assert c.patch(f'/api/orgs/{org}/members/{owner_id}',json={'role':'viewer'},headers=h).status_code==409
    assert c.patch(f'/api/orgs/{org}/members/{viewer_id}',json={'role':'owner'},headers=h).status_code==422


def test_weak_or_reused_password_does_not_revoke_session(env):
    app,c,_=env;h=login(c)
    assert c.post('/api/auth/password',headers=h,json={'current_password':'correct-password','new_password':'short'}).status_code==422
    assert c.post('/api/auth/password',headers=h,json={'current_password':'correct-password','new_password':'correct-password'}).status_code==422
    assert c.get('/api/auth/me').status_code==200
    with pytest.raises(ValueError):reset_password(app.state.db,'owner@example.test','new-secure-password-123',identity_verified=True,reference='x'*65)


def test_administrator_cannot_manage_members(env):
    app,c,(org,*_)=env;h=login(c)
    viewer=TestClient(app);vh=login(viewer,'viewer@example.test');uid=viewer.get('/api/auth/me').json()['id']
    assert c.patch(f'/api/orgs/{org}/members/{uid}',json={'role':'administrator'},headers=h).status_code==200
    assert viewer.get(f'/api/orgs/{org}/audit').status_code==200
    assert viewer.patch(f'/api/orgs/{org}/members/{uid}',json={'role':'developer'},headers=vh).status_code==403
