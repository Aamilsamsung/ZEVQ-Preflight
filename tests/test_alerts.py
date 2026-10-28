import time
from test_api import env,login
from app.db import Scan

def test_durable_failure_delay_alerts_scoped_and_acknowledged(env):
    app,c,(org,foreign,*_)=env;h=login(c)
    with app.state.db() as db:
        db.add_all([Scan(org_id=org,status='failed') for _ in range(3)]+[Scan(org_id=org,status='running',updated_at=time.time()-200),Scan(org_id=org,status='queued',created_at=time.time()-400),Scan(org_id=foreign,status='failed')]);db.commit()
    root=f'/api/orgs/{org}/alerts';data=c.get(root).json();assert len(data['alerts'])==6
    assert data['alerts'][0]['title']=='Repeated scan failures' and data['external_delivery']=='disabled'
    aid=data['alerts'][0]['id'];assert c.post(root+'/'+aid+'/acknowledge',headers=h).status_code==200
    assert c.get(root).json()['alerts'][0]['acknowledged']
    assert c.get(f'/api/orgs/{foreign}/alerts').status_code==404
    assert c.post(root+'/failed:missing/acknowledge',headers=h).status_code==404
    login(c,'viewer@example.test');assert not c.get(root).json()['alerts'][0]['acknowledged']
    assert c.post(root+'/'+aid+'/acknowledge').status_code==403

def test_idle_does_not_claim_worker_health_or_alert(env):
    _,c,(org,*_)=env;login(c)
    data=c.get(f'/api/orgs/{org}/alerts').json();assert data['alerts']==[] and 'no out-of-band' in data['scope'].lower()
