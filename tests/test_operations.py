import time
from sqlalchemy import event
from test_api import env
from app.db import Scan


def test_health_detects_database_failure_without_details(env):
    app,c,_=env
    assert c.get('/health').json()['database']=='reachable'
    def fail(*args):raise RuntimeError('secret connection password')
    event.listen(app.state.health_engine,'before_cursor_execute',fail)
    try:
        r=c.get('/health');assert r.status_code==503 and 'secret' not in r.text
    finally:event.remove(app.state.health_engine,'before_cursor_execute',fail)


def test_monitor_is_disabled_without_secret_and_rejects_wrong_token(env,monkeypatch):
    _,c,_=env
    monkeypatch.delenv('PREFLIGHT_MONITOR_TOKEN',raising=False)
    assert c.get('/api/operations/monitor').status_code==404
    monkeypatch.setenv('PREFLIGHT_MONITOR_TOKEN','synthetic-monitor-token-32-characters')
    assert c.get('/api/operations/monitor',headers={'Authorization':'Bearer wrong'}).status_code==404


def test_monitor_signals_are_aggregate_without_source_or_identity(env,monkeypatch):
    app,c,(org,*_)=env;token='synthetic-monitor-token-32-characters';monkeypatch.setenv('PREFLIGHT_MONITOR_TOKEN',token)
    headers={'Authorization':'Bearer '+token}
    assert c.get('/api/operations/monitor',headers=headers).json()['status']=='ok'
    with app.state.db() as db:
        db.add_all([Scan(org_id=org,status='failed',error='private-source') for _ in range(3)])
        db.add(Scan(org_id=org,status='queued',created_at=time.time()-301))
        db.add(Scan(org_id=org,status='running',updated_at=time.time()-181));db.commit()
    r=c.get('/api/operations/monitor',headers=headers)
    assert all(r.json()['signals'].values()) and r.json()['status']=='degraded'
    assert org not in r.text and 'private-source' not in r.text
