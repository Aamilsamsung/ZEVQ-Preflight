import time
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from test_api import env, login
from app import email_recovery as mail
from app.db import EmailToken, User, Audit
from app.security import digest
ORIGINAL_DELIVER = mail.deliver


@pytest.fixture
def delivery(monkeypatch):
    for k,v in {'PREFLIGHT_EMAIL_ENABLED':'1','PUBLIC_ORIGIN':'https://preflight.test','PREFLIGHT_SMTP_HOST':'smtp.example.test','PREFLIGHT_SMTP_FROM':'support@example.test','PREFLIGHT_SMTP_USERNAME':'fixture','PREFLIGHT_SMTP_PASSWORD':'fixture-secret'}.items():monkeypatch.setenv(k,v)
    sent=[]
    monkeypatch.setattr(mail,'deliver',lambda config,recipient,purpose,token:sent.append((recipient,purpose,token)))
    return sent


def request(c,email='owner@example.test',purpose='reset'):
    path='request-reset' if purpose=='reset' else 'request-verification'
    return c.post('/api/auth/email/'+path,json={'email':email})


def test_disabled_email_never_claims_delivery(env,monkeypatch):
    _,c,_=env;monkeypatch.delenv('PREFLIGHT_EMAIL_ENABLED',raising=False)
    assert c.get('/api/auth/email/status').json()['delivery_enabled'] is False
    assert request(c).status_code==503
    assert c.post('/api/auth/email/reset',json={'token':'x','new_password':'long-enough-password'}).status_code==503


def test_reset_single_use_hash_only_and_all_sessions_revoked(env,delivery):
    app,c,_=env;login(c);second=TestClient(app);login(second)
    assert request(c).status_code==202
    raw=delivery[0][2]
    with app.state.db() as db:
        row=db.scalar(select(EmailToken));assert row.token_hash==digest(raw) and raw not in repr(row.__dict__)
    response=c.post('/api/auth/email/reset',json={'token':raw,'new_password':'new-secure-password-123'})
    assert response.status_code==200
    assert second.get('/api/auth/me').status_code==401
    assert c.post('/api/auth/email/reset',json={'token':raw,'new_password':'another-password-123'}).status_code==400
    assert c.post('/api/auth/login',json={'email':'owner@example.test','password':'correct-password'}).status_code==401
    assert c.post('/api/auth/login',json={'email':'owner@example.test','password':'new-secure-password-123'}).status_code==200
    with app.state.db() as db:assert db.scalar(select(Audit).where(Audit.action=='account.password_reset_email'))


def test_nonexistent_and_unverified_reset_indistinguishable(env,delivery):
    app,c,_=env
    a=request(c);b=request(c,'absent@example.test')
    with app.state.db() as db:
        db.add(User(email='pending@example.test',password_hash='not-used',verified=0));db.commit()
    d=request(c,'pending@example.test')
    assert a.status_code==b.status_code==d.status_code==202
    assert a.json()==b.json()==d.json() and len(delivery)==1


def test_expired_wrong_purpose_and_invalid_links(env,delivery):
    app,c,_=env;request(c);raw=delivery[0][2]
    assert c.post('/api/auth/email/verify',json={'token':raw}).status_code==400
    assert c.post('/api/auth/email/reset',json={'token':'bad','new_password':'new-secure-password-123'}).status_code==400
    with app.state.db() as db:db.scalar(select(EmailToken)).expires=time.time()-1;db.commit()
    assert c.post('/api/auth/email/reset',json={'token':raw,'new_password':'new-secure-password-123'}).status_code==400


def test_email_verification_does_not_register(env,delivery):
    app,c,_=env
    with app.state.db() as db:
        db.add(User(email='pending@example.test',password_hash='unused',verified=0));db.commit()
    assert request(c,'pending@example.test','verify').status_code==202
    token=delivery[0][2]
    assert c.post('/api/auth/email/verify',json={'token':token}).status_code==200
    assert c.post('/api/auth/email/verify',json={'token':token}).status_code==400
    with app.state.db() as db:assert db.scalar(select(User).where(User.email=='pending@example.test')).verified==1
    assert c.post('/api/auth/register',json={}).status_code==403


def test_resend_invalidates_previous_token(env,delivery):
    _,c,_=env;request(c);request(c)
    assert c.post('/api/auth/email/reset',json={'token':delivery[0][2],'new_password':'new-secure-password-123'}).status_code==400
    assert c.post('/api/auth/email/reset',json={'token':delivery[1][2],'new_password':'new-secure-password-123'}).status_code==200


def test_password_change_invalidates_email_links(env,delivery):
    _,c,_=env;headers=login(c);request(c);raw=delivery[0][2]
    assert c.post('/api/auth/password',headers=headers,json={'current_password':'correct-password','new_password':'new-secure-password-123'}).status_code==200
    assert c.post('/api/auth/email/reset',json={'token':raw,'new_password':'another-secure-password'}).status_code==400


def test_failed_provider_is_generic_and_token_disabled(env,delivery,monkeypatch):
    app,c,_=env
    def fail(*args):raise RuntimeError('provider-secret-token')
    monkeypatch.setattr(mail,'deliver',fail)
    r=request(c);assert r.status_code==202 and 'provider-secret' not in r.text
    with app.state.db() as db:
        assert db.scalar(select(EmailToken)).consumed_at
        assert db.scalar(select(Audit).where(Audit.action=='account.email_reset_failed'))


def test_recipient_limit_and_cross_origin(env,delivery):
    _,c,_=env
    for _ in range(3):assert request(c).status_code==202
    assert request(c).status_code==429
    assert c.post('/api/auth/email/request-reset',headers={'Origin':'https://evil.test'},json={'email':'owner@example.test'}).status_code==403


@pytest.mark.parametrize('key,value',[('PUBLIC_ORIGIN','http://insecure.test'),('PUBLIC_ORIGIN','https://safe.test@evil.test'),('PREFLIGHT_SMTP_PORT','25'),('PREFLIGHT_SMTP_FROM','bad\nheader@example.test')])
def test_insecure_config_is_disabled(delivery,monkeypatch,key,value):
    monkeypatch.setenv(key,value);assert mail.configuration() is None


@pytest.mark.parametrize('port',[465,587])
def test_smtp_requires_tls_before_auth(delivery,monkeypatch,port):
    calls=[]
    class SMTP:
        def __init__(self,*args,**kwargs):
            calls.append(('open',kwargs.get('context')))
            assert kwargs['timeout']==10
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def ehlo(self):calls.append(('ehlo',None))
        def starttls(self,context):calls.append(('tls',context));assert context.check_hostname
        def login(self,*args):calls.append(('auth',None))
        def send_message(self,msg):
            calls.append(('send',None));assert '#token=' in msg.get_content()
            assert '?token=' not in msg.get_content()
    monkeypatch.setattr(mail.smtplib,'SMTP_SSL',SMTP);monkeypatch.setattr(mail.smtplib,'SMTP',SMTP)
    config=mail.configuration();config['port']=port
    # fixture patches deliver; invoke the original function saved at collection.
    ORIGINAL_DELIVER(config,'owner@example.test','reset','x'*64)
    if port==587:assert [c[0] for c in calls].index('tls')<[c[0] for c in calls].index('auth')
    else:assert calls[0][1].check_hostname


@pytest.mark.skipif(not __import__('os').getenv('TEST_DATABASE_URL'),reason='PostgreSQL token row-lock verification')
def test_parallel_reset_consumes_token_once(env,delivery):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import HTTPException
    app,c,_=env;request(c);token=delivery[0][2]
    def consume(_):
        try:mail.consume(app.state.db,token,'reset','parallel-secure-password-123');return 200
        except HTTPException as exc:return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:assert sorted(pool.map(consume,range(2)))==[200,400]
