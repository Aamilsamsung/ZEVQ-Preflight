"""Organization-scoped in-app operational signals from durable scan records."""
import time
from sqlalchemy import select
from .db import Scan,Audit

def current_alerts(db,org,actor):
    now=time.time()
    rows=db.scalars(select(Scan).where(Scan.org_id==org,Scan.created_at>now-7*86400,Scan.status.in_(('failed','queued','running'))).order_by(Scan.created_at.desc()).limit(100)).all()
    alerts=[];recent=[]
    for scan in rows:
        if scan.status=='failed':
            alerts.append({'id':'failed:'+scan.id,'scan_id':scan.id,'severity':'high','title':'Scan failed','message':'Open the report for the recorded failure and request reference. No successful analysis is implied.','created_at':scan.updated_at})
            if scan.updated_at>now-3600:recent.append(scan)
        elif (scan.status=='running' and scan.updated_at<now-180) or (scan.status=='queued' and scan.created_at<now-300):
            alerts.append({'id':'delayed:'+scan.id,'scan_id':scan.id,'severity':'medium','title':'Scan processing delayed','message':'The stored job exceeded its normal lease/queue threshold. Inspect worker diagnostics; this signal does not prove the worker is down.','created_at':scan.updated_at})
    if len(recent)>=3:
        alerts.insert(0,{'id':'repeated:'+recent[0].id,'scan_id':recent[0].id,'severity':'high','title':'Repeated scan failures','message':str(len(recent))+' failures observed in the last hour within the bounded monitoring window.','created_at':recent[0].updated_at})
    keys=['alert.ack:'+a['id'] for a in alerts]
    acknowledged=set(db.scalars(select(Audit.action).where(Audit.org_id==org,Audit.actor_id==actor,Audit.action.in_(keys))))
    return {'alerts':[{**a,'acknowledged':'alert.ack:'+a['id'] in acknowledged} for a in alerts],
            'scope':'Latest100 failed/queued/running scans created in the last7 days. In-app delivery only; no out-of-band availability monitor.',
            'external_delivery':'disabled','thresholds':{'repeated_failures_per_hour':3,'running_stale_seconds':180,'queued_delay_seconds':300}}
