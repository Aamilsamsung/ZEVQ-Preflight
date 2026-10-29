import pytest
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from test_api import env,login
from test_email_recovery import delivery
from app import onboarding
from app.db import User,Organization,Scan,AccountEvent,EmailToken

@pytest.fixture
def enabled(delivery,monkeypatch):
    monkeypatch.setenv('PREFLIGHT_REGISTRATION_ENABLED','1');monkeypatch.setenv('PREFLIGHT_LEGAL_APPROVED_VERSION',onboarding.LEGAL_VERSION)
    return delivery


def signup(c,email='new@example.test',**kw):
    return c.post('/api/auth/register',json={'email':email,'accepted_terms':True,'legal_version':onboarding.LEGAL_VERSION,**kw})


def test_closed_until_email_and_legal_approval(env,monkeypatch):
    _,c,_=env;monkeypatch.setenv('PREFLIGHT_REGISTRATION_ENABLED','1')
    assert signup(c).status_code==403


def test_registration_mail_proof_password_org_and_isolation(env,enabled):
    app,c,(old_org,*_)=env
    assert signup(c).status_code==202;assert len(enabled)==1
    assert c.get('/api/auth/me').status_code==401
    with app.state.db() as db:
        user=db.scalar(select(User).where(User.email=='new@example.test'))
        assert user.verified==0 and user.registration_pending==1
        assert db.scalar(select(func.count()).select_from(Organization))==2
        assert db.scalar(select(AccountEvent).where(AccountEvent.user_id==user.id)).action.endswith(onboarding.LEGAL_VERSION)
    token=enabled[0][2]
    assert c.post('/api/auth/email/verify',json={'token':token}).status_code==422
    assert c.post('/api/auth/email/verify',json={'token':token,'new_password':'new-mailbox-owned-password'}).status_code==200
    assert c.post('/api/auth/email/verify',json={'token':token,'new_password':'new-mailbox-owned-password'}).status_code==400
    auth=c.post('/api/auth/login',json={'email':'new@example.test','password':'new-mailbox-owned-password'});assert auth.status_code==200
    assert c.get('/api/auth/me').json()['organizations']==[]
    org=c.post('/api/orgs',headers={'X-CSRF-Token':auth.json()['csrf_token']},json={'name':'Verified workspace'});assert org.status_code==201
    assert c.get(f'/api/orgs/{old_org}/scans').status_code==404
    assert c.get('/api/auth/export').json()['account_events']


def test_pre_registration_never_sets_attacker_chosen_password(env,enabled):
    app,c,_=env
    assert signup(c,'victim@example.test',password='attacker-selected-password').status_code==202
    assert signup(c,'VICTIM@example.test').status_code==202
    # First email is invalidated by resend; only mailbox holder can choose password.
    assert c.post('/api/auth/email/verify',json={'token':enabled[0][2],'new_password':'mailbox-holder-password'}).status_code==400
    assert c.post('/api/auth/email/verify',json={'token':enabled[1][2],'new_password':'mailbox-holder-password'}).status_code==200
    assert c.post('/api/auth/login',json={'email':'victim@example.test','password':'attacker-selected-password'}).status_code==401
    assert c.post('/api/auth/login',json={'email':'victim@example.test','password':'mailbox-holder-password'}).status_code==200


def test_existing_account_is_not_overwritten_or_enumerated(env,enabled):
    _,c,_=env
    existing=signup(c,'owner@example.test');fresh=signup(c)
    assert existing.status_code==fresh.status_code==202 and existing.json()==fresh.json()
    assert len(enabled)==1
    login(c)


@pytest.mark.parametrize('change',[{'accepted_terms':False},{'accepted_terms':'yes'},{'legal_version':'old'},{'email':'bad\naddress@example.test'},{'email':'x@bad..example.test'}])
def test_invalid_consent_or_address_rejected(env,enabled,change):
    _,c,_=env;assert signup(c,**change).status_code==422 and not enabled


def test_registration_ip_and_resend_limits(env,enabled):
    _,c,_=env
    for _ in range(3):assert signup(c).status_code==202
    assert signup(c).status_code==429
    assert signup(c,'second@example.test').status_code==202
    assert signup(c,'third@example.test').status_code==429


def test_registration_cross_origin_rejected(env,enabled):
    _,c,_=env
    r=c.post('/api/auth/register',headers={'Origin':'https://evil.test'},json={'email':'new@example.test','accepted_terms':True,'legal_version':onboarding.LEGAL_VERSION})
    assert r.status_code==403 and not enabled


def test_account_scan_quota_covers_other_orgs(env):
    app,c,(org,other,uid,*_)=env;h=login(c)
    with app.state.db() as db:db.add_all([Scan(org_id=other,created_by=uid,status='completed') for _ in range(20)]);db.commit()
    pair={'baseline':{'openapi':'3.0.3','paths':{}},'proposed':{'openapi':'3.0.3','paths':{}}}
    assert c.post(f'/api/orgs/{org}/contracts',headers=h,json=pair).status_code==429


def test_expensive_password_work_is_bounded_without_weakening_hash_settings():
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException
    from app.security import BoundedPasswordHasher
    gate=threading.Event();both=threading.Event();lock=threading.Lock();started=0
    class Slow:
        def hash(self,password):
            nonlocal started
            with lock:
                started+=1
                if started==2:both.set()
            assert gate.wait(3)
            return 'fixture-hash'
    bounded=BoundedPasswordHasher(Slow(),timeout=0.05)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(bounded.hash,'fixture-password') for _ in range(2)]
        try:
            assert both.wait(2)
            with pytest.raises(HTTPException) as busy:bounded.hash('another-fixture')
            assert busy.value.status_code==503 and started==2
        finally:gate.set()
        assert all(job.result()=='fixture-hash' for job in jobs)


def test_oversized_auth_bodies_rejected_before_parsing(env):
    _,c,_=env
    for path in ['register','login','email/reset']:
        response=c.post('/api/auth/'+path,content=b'x'*17000,headers={'Content-Type':'application/json'})
        assert response.status_code==413 and 'x'*100 not in response.text
    assert c.post('/api/auth/login',content=iter([b'x'*9000,b'x'*9000]),headers={'Content-Type':'application/json'}).status_code==413


def test_production_mode_fails_closed_without_postgres_and_rejects_unknown_mode(tmp_path,monkeypatch):
    from app.main import create_app
    app=create_app('sqlite:///'+str(tmp_path/'closed.db'),mode='production')
    with pytest.raises(RuntimeError,match='PostgreSQL'):
        with TestClient(app):pass
    with pytest.raises(ValueError,match='Unsupported'):create_app(mode='prod-typo')


def test_production_mode_secure_cookies_and_public_marketing_only(env,monkeypatch):
    from app.main import create_app
    app,_,_=env
    production=create_app(str(app.state.engine.url),mode='production')
    # Startup PostgreSQL validation is tested separately; this disposable SQLite
    # fixture exercises HTTPS middleware/cookie behavior without a live host.
    client=TestClient(production,base_url='https://testserver',follow_redirects=False)
    monkeypatch.setenv('PREFLIGHT_PUBLIC_ACCESS_ENABLED','1')
    assert client.get('/').status_code==200
    assert client.get('/api/auth/me').status_code==401
    result=client.post('/api/auth/login',json={'email':'owner@example.test','password':'correct-password'})
    assert result.status_code==200 and 'Secure' in result.headers['set-cookie'] and 'HttpOnly' in result.headers['set-cookie']
    assert result.headers['strict-transport-security']=='max-age=31536000'
    assert client.get('/api/auth/me').status_code==200
    client.close();production.state.engine.dispose();production.state.health_engine.dispose()


def test_sqlite_additive_migration_preserves_scan_and_review_data(tmp_path,monkeypatch):
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine,text
    url='sqlite:///'+str(tmp_path/'preserve.db')
    monkeypatch.setenv('DATABASE_URL_UNPOOLED',url)
    config=Config('alembic.ini');command.upgrade(config,'0005')
    engine=create_engine(url)
    with engine.begin() as db:
        db.execute(text('PRAGMA foreign_keys=ON'))
        db.execute(text("INSERT INTO users(id,email,password_hash,verified) VALUES('u','fixture@example.test','fixture-not-a-password',1)"))
        db.execute(text("INSERT INTO organizations(id,name) VALUES('o','Fixture')"))
        db.execute(text("INSERT INTO scans(id,org_id,repository,base_ref,head_ref,status,created_at,updated_at,attempts) VALUES('s','o','fixture','','','completed',1,1,1)"))
        db.execute(text("INSERT INTO finding_reviews(scan_id,finding_id,version,status,reason,actor_id,updated_at) VALUES('s','f',1,'acknowledged','Preserve this review','u',1)"))
    command.upgrade(config,'head')
    with engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM finding_reviews')).scalar_one()==1
        assert db.execute(text('SELECT registration_pending FROM users')).scalar_one()==0
        assert db.execute(text('SELECT created_by FROM scans')).scalar_one() is None
        assert db.execute(text('PRAGMA foreign_key_check')).all()==[]
    command.downgrade(config,'0005')
    with engine.connect() as db:assert db.execute(text('SELECT count(*) FROM finding_reviews')).scalar_one()==1
    engine.dispose()


@pytest.mark.skipif(not __import__('os').getenv('TEST_DATABASE_URL'),reason='PostgreSQL cross-organization admission locks')
def test_concurrent_cross_org_submissions_cannot_exceed_account_quota(env):
    from concurrent.futures import ThreadPoolExecutor
    app,c,(org,_,uid,*_)=env;h=login(c)
    other=c.post('/api/orgs',headers=h,json={'name':'Second owned workspace'}).json()['id']
    second=TestClient(app);h2=login(second)
    with app.state.db() as db:db.add_all([Scan(org_id=org,created_by=uid,status='completed') for _ in range(19)]);db.commit()
    pair={'baseline':{'openapi':'3.0.3','paths':{}},'proposed':{'openapi':'3.0.3','paths':{}}}
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(c.post,f'/api/orgs/{org}/contracts',headers=h,json=pair)
        another=pool.submit(second.post,f'/api/orgs/{other}/contracts',headers=h2,json=pair)
        assert sorted([first.result(timeout=10).status_code,another.result(timeout=10).status_code])==[202,429]
    with app.state.db() as db:assert db.scalar(select(func.count()).select_from(Scan).where(Scan.created_by==uid))==20
    second.close()
