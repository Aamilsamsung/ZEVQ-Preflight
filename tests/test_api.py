import io
import os
import json
import time
import zipfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import create_app
from app.db import Base, User, Organization, Membership, Scan, SessionRecord
from app.security import hasher

@pytest.fixture
def env(tmp_path):
    database_url = os.getenv('TEST_DATABASE_URL') or 'sqlite:///' + str(tmp_path / 'test.db')
    app = create_app(database_url, mode='development')
    if os.getenv('TEST_DATABASE_URL'):
        Base.metadata.drop_all(app.state.engine)
    Base.metadata.create_all(app.state.engine)
    with app.state.db() as db:
        a = User(email='owner@example.test', password_hash=hasher.hash('correct-password'), verified=1)
        b = User(email='other@example.test', password_hash=hasher.hash('correct-password'), verified=1)
        v = User(email='viewer@example.test', password_hash=hasher.hash('correct-password'), verified=1)
        x, y = Organization(name='First'), Organization(name='Second')
        db.add_all([a,b,v,x,y]); db.flush()
        db.add_all([Membership(org_id=x.id,user_id=a.id,role='owner'), Membership(org_id=y.id,user_id=b.id,role='owner'), Membership(org_id=x.id,user_id=v.id,role='viewer')]); db.commit()
        ids = (x.id,y.id,a.id,b.id)
    with TestClient(app) as client:
        yield app,client,ids

def login(client, email='owner@example.test'):
    r=client.post('/api/auth/login',json={'email':email,'password':'correct-password'})
    assert r.status_code==200, r.text
    return {'X-CSRF-Token':r.json()['csrf_token']}

def test_session_csrf_logout(env):
    app,c,(org,other,*_) = env
    h=login(c)
    assert c.get('/api/auth/me').json()['organizations'][0]['id']==org
    assert c.cookies.get('preflight_session')
    assert c.post('/api/orgs',json={'name':'Denied'}).status_code==403
    assert c.post('/api/orgs',json={'name':'Denied'},headers={**h,'Origin':'https://evil.test'}).status_code==403
    assert c.post('/api/auth/logout',headers=h).status_code==200
    assert c.get('/api/auth/me').status_code==401

def test_expiration_and_revoke_all(env):
    app,c,_=env
    h=login(c)
    with TestClient(app) as second:
        login(second)
        assert c.post('/api/auth/logout-all',headers=h).status_code==200
        assert second.get('/api/auth/me').status_code==401
    login(c)
    with app.state.db() as db:
        for s in db.scalars(select(SessionRecord)): s.expires=time.time()-1
        db.commit()
    assert c.get('/api/auth/me').status_code==401

@pytest.mark.parametrize('suffix',['repos','scans','dashboard','members','audit'])
def test_tenant_reads(env,suffix):
    _,c,(_,other,*_)=env
    login(c)
    assert c.get(f'/api/orgs/{other}/{suffix}').status_code==404

@pytest.mark.parametrize('suffix,payload',[('repos',{'full_name':'owner/repo'}),('scans',{'repository_id':'x'}),('members',{'email':'x','role':'viewer'})])
def test_viewer_writes(env,suffix,payload):
    _,c,(org,*_)=env
    h=login(c,'viewer@example.test')
    assert c.post(f'/api/orgs/{org}/{suffix}',json=payload,headers=h).status_code==403

def test_closed_registration_and_legacy(env):
    _,c,_=env
    assert c.post('/api/auth/register',json={}).status_code==403
    assert c.post('/api/scan/zip').status_code==401

def test_repo_scan_idempotency_and_quota(env):
    _,c,(org,*_)=env
    h=login(c); path=f'/api/orgs/{org}'
    repo=c.post(path+'/repos',json={'full_name':'test/repo'},headers=h).json()['id']
    body={'repository_id':repo,'head_ref':'main'}
    r=c.post(path+'/scans',json=body,headers={**h,'Idempotency-Key':'one'})
    assert r.status_code==202
    assert c.post(path+'/scans',json=body,headers={**h,'Idempotency-Key':'one'}).json()['id']==r.json()['id']
    assert c.post(path+'/scans',json={**body,'head_ref':'different'},headers={**h,'Idempotency-Key':'one'}).status_code==409
    for _ in range(2): assert c.post(path+'/scans',json=body,headers=h).status_code==202
    assert c.post(path+'/scans',json=body,headers=h).status_code==429
    assert c.post(path+'/scans/'+r.json()['id']+'/cancel',headers=h).status_code==200
    assert c.post(path+'/scans',json=body,headers=h).status_code==202

def test_foreign_scan_and_csv(env):
    app,c,(org,other,*_)=env
    with app.state.db() as db:
        s=Scan(org_id=other,status='completed',result=json.dumps({'findings':[{'message':'=DANGEROUS()','severity':'high'}]}))
        db.add(s); db.commit(); sid=s.id
    h=login(c)
    for suffix in ('','/report'):
        assert c.get(f'/api/orgs/{org}/scans/{sid}'+suffix).status_code==404
    assert c.post(f'/api/orgs/{org}/scans/{sid}/cancel',headers=h).status_code==404
    login(c,'other@example.test')
    response=c.get(f'/api/orgs/{other}/scans/{sid}/report?format=csv')
    assert response.status_code==200
    assert "'=DANGEROUS()" in response.text

def test_malicious_zip(env):
    _,c,(org,*_)=env
    h=login(c)
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w') as z: z.writestr('../evil.py','pass')
    assert c.post(f'/api/orgs/{org}/scans/zip',files={'file':('x.zip',data.getvalue())},headers=h).status_code==422

def test_invalid_credentials_and_rate_limit(env):
    _,c,_=env
    for _ in range(10):
        assert c.post('/api/auth/login',json={'email':'none@test','password':'bad'}).status_code==401
    assert c.post('/api/auth/login',json={'email':'none@test','password':'bad'}).status_code==429

def test_account_delete_ownership_guard(env):
    _,c,(org,*_)=env
    h=login(c)
    assert c.delete('/api/auth/account',headers=h).status_code==409
    assert c.delete(f'/api/orgs/{org}',headers=h).status_code==200
    assert c.delete('/api/auth/account',headers=h).status_code==200
    assert c.get('/api/auth/me').status_code==401


def test_chunked_body_limit(env):
    _,c,_=env
    def oversized():
        for _ in range(17):
            yield b'x' * 1_000_000
    response=c.post('/api/auth/login',content=oversized(),headers={'Content-Type':'application/json'})
    assert 'content-length' not in response.request.headers
    assert response.status_code==413

def test_dashboard_chart_evidence_is_tenant_scoped(env):
    app,c,(org,other,*_)=env
    login(c)
    with app.state.db() as db:
        db.add_all([
            Scan(org_id=org, status='completed', result=json.dumps({'findings':[{'severity':'high','message':'Visible evidence','file':'app.py'}]})),
            Scan(org_id=other, status='completed', result=json.dumps({'findings':[{'severity':'critical','message':'Private other tenant'}]}))
        ])
        db.commit()
    data=c.get(f'/api/orgs/{org}/dashboard').json()
    assert data['findings']==1
    assert len(data['finding_trend'])==7
    assert sum(day['count'] for day in data['finding_trend'])==1
    assert data['latest_findings'][0]['message']=='Visible evidence'
    assert 'Private other tenant' not in json.dumps(data)
