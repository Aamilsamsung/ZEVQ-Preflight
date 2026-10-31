import json,logging
import pytest
from fastapi import HTTPException,Request
from fastapi.testclient import TestClient
from sqlalchemy import event,delete
from test_api import env,login
from app.security import principal,has_active_session
from app.db import SessionRecord


def request(app,c,h=None):
    headers=[(b'cookie',('preflight_session='+c.cookies.get('preflight_session')).encode())]
    if h:headers.append((b'x-csrf-token',h['X-CSRF-Token'].encode()))
    return Request({'type':'http','method':'POST','path':'/','headers':headers,'app':app})


def test_one_auth_query_per_request_and_csrf_still_required(env):
    app,c,_=env;h=login(c);queries=[]
    def count(*args):queries.append(1)
    event.listen(app.state.engine,'before_cursor_execute',count)
    try:
        req=request(app,c,h);assert has_active_session(req);principal(req);principal(req);assert len(queries)==1
        req=request(app,c);assert has_active_session(req)
        with pytest.raises(HTTPException) as denied:principal(req)
        assert denied.value.status_code==403
        assert len(queries)==2
    finally:event.remove(app.state.engine,'before_cursor_execute',count)


def test_identity_never_cached_between_requests(env):
    app,c,_=env;h=login(c);assert has_active_session(request(app,c,h))
    with app.state.db() as db:db.execute(delete(SessionRecord));db.commit()
    assert not has_active_session(request(app,c,h))
    assert c.get('/api/auth/me').status_code==401


def test_structured_logs_exclude_secrets_and_raw_urls(env,caplog):
    app,c,(org,*_)=env;login(c)
    app.state.engine.dispose()
    with caplog.at_level(logging.INFO,logger='uvicorn.error'):
        r=c.get(f'/api/orgs/{org}/scans?token=synthetic-sensitive-query',headers={'X-Request-ID':'synthetic-untrusted-id'})
    assert r.status_code==200 and len(r.headers['x-request-id'])==32
    assert r.headers['x-request-id']!='synthetic-untrusted-id' and 'db;dur=' in r.headers['server-timing']
    records=[json.loads(x.message) for x in caplog.records if x.message.startswith('{')]
    entry=next(x for x in records if x['request_id']==r.headers['x-request-id'])
    assert entry['route']=='/api/orgs/{org_id}/scans' and entry['queries']>0 and entry['db_ms']>=0 and entry['connect_ms']>=0
    assert org not in json.dumps(records) and 'synthetic-sensitive-query' not in json.dumps(records)
    assert 'synthetic-untrusted-id' not in json.dumps(records)


def test_unhandled_error_has_safe_reference(env):
    app,_,_=env
    @app.get('/synthetic-error')
    def broken():raise RuntimeError('synthetic-secret-source-must-not-echo')
    app.router.routes.insert(0,app.router.routes.pop())
    with TestClient(app,raise_server_exceptions=False) as c:r=c.get('/synthetic-error')
    assert r.status_code==500 and 'synthetic-secret-source' not in r.text
    assert r.headers['x-request-id'] in r.json()['detail']
    assert r.headers['cache-control']=='no-store' and r.headers['x-content-type-options']=='nosniff'


def test_early_error_has_request_reference(env):
    _,c,_=env;r=c.get('/api/auth/me');assert r.status_code==401
    assert len(r.headers['x-request-id'])==32 and 'app;dur=' in r.headers['server-timing']
