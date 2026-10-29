"""CI-only rollback read/auth compatibility on the restored disposable schema. Never migrates."""
import json,os,subprocess
from pathlib import Path
from urllib.parse import urlsplit
url=os.getenv('DATABASE_URL','');parsed=urlsplit(url);source=Path(os.environ.get('PREFLIGHT_ROLLBACK_SOURCE','/nonexistent')).resolve()
expected='9e78cde832e0d9213aae6450c5fb7d80f90ff6f4'
if os.getenv('CI')!='true' or parsed.hostname not in ('localhost','127.0.0.1') or parsed.path!='/preflight_restore' or not source.is_dir():raise SystemExit('Disposable local CI restore database and trusted rollback source required')
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD']).decode().strip()==expected
from fastapi.testclient import TestClient
import app.main as previous
from sqlalchemy import text
assert Path(previous.__file__).resolve().is_relative_to(source),'Rollback must load the previous application, not the current checkout'
data=json.loads(Path(os.environ['PREFLIGHT_RESTORE_MANIFEST']).read_text());application=previous.create_app(url,mode='development')
with application.state.engine.connect() as conn:
 assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0004'
with TestClient(application) as client:
 client.cookies.set('preflight_session','ci-only-restored-session-token')
 assert client.get('/api/auth/me').json()['email']=='restore-owner@example.test'
 report=client.get(f'/api/orgs/{data["org_id"]}/scans/{data["scan_id"]}/report').json()
 assert report['reviews'][data['finding_id']]['status']=='acknowledged'
 assert len(client.get(f'/api/orgs/{data["org_id"]}/scans/{data["scan_id"]}/findings/{data["finding_id"]}/reviews').json())==1
 client.cookies.clear()
 assert client.post('/api/auth/login',json={'email':'restore-other@example.test','password':'ci-only-restore-password-strong'}).status_code==200
 assert client.get(f'/api/orgs/{data["org_id"]}/scans/{data["scan_id"]}/report').status_code==404
from app.db import Scan
from app.worker import claim, execute
with application.state.db() as db:
 queued=Scan(org_id=data['org_id'],status='queued',created_at=-1,payload=json.dumps({'contracts':{'baseline':{'openapi':'3.0.3','paths':{}},'proposed':{'openapi':'3.0.3','paths':{}}}}));db.add(queued);db.commit();queued_id=queued.id
job=claim(application.state.db);assert job and job[0]==queued_id;execute(application.state.db,*job)
with application.state.db() as db:
 completed=db.get(Scan,queued_id);assert completed.status=='completed' and json.loads(completed.result)['simulation']['status']=='not-executed'
with application.state.engine.connect() as conn:
 assert conn.execute(text('SELECT version_num FROM alembic_version')).scalar_one()=='0004'
 assert conn.execute(text('SELECT count(*) FROM retention_policies')).scalar_one()>0
Path(os.environ['PREFLIGHT_ROLLBACK_SUMMARY']).write_text(json.dumps({'previous_commit':expected,'current_schema':'0004','fallback_static_worker':True,'restored_session':True,'report_and_reviews':True,'history':True,'tenant_isolation':True,'schema_and_retention_preserved':True,'scope':'Previous application against a restored disposable PostgreSQL16 CI database; not a hosted service rollback'},indent=2))
print('Rollback compatibility passed: previous source, existing session, report/reviews/history, tenant isolation and additive schema preservation')
