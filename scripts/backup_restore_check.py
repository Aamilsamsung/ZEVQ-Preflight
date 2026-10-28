"""CI-only synthetic PostgreSQL restore exercise. Never runs against customer data."""
import json,os,sys,time
from pathlib import Path
from urllib.parse import urlsplit
from sqlalchemy import select,func
from fastapi.testclient import TestClient
from app.db import Base,User,Organization,Membership,Scan,Repository,make_engine,factory
from app.security import hasher
from app.analyzer import analyze
from app.main import create_app

command=sys.argv[1] if len(sys.argv)>1 else ''
url=os.environ.get('DATABASE_URL','');parsed=urlsplit(url)
expected='preflight_test' if command=='seed' else 'preflight_restore'
if os.getenv('CI')!='true' or parsed.hostname not in ('localhost','127.0.0.1') or parsed.path!='/'+expected or command not in ('seed','verify'):
    raise SystemExit('This helper requires the named disposable local CI PostgreSQL database')
manifest=Path('artifacts/restore-manifest.json');summary=Path('artifacts/restore-results.json');manifest.parent.mkdir(exist_ok=True)
engine=make_engine(url);db_factory=factory(engine);password='ci-only-restore-password-strong'
try:
 if command=='seed':
  with db_factory() as db:
   first=User(email='restore-owner@example.test',password_hash=hasher.hash(password),verified=1);second=User(email='restore-other@example.test',password_hash=hasher.hash(password),verified=1)
   a,b=Organization(name='Restore synthetic A'),Organization(name='Restore synthetic B');db.add_all([first,second,a,b]);db.flush()
   db.add_all([Membership(org_id=a.id,user_id=first.id,role='owner'),Membership(org_id=b.id,user_id=second.id,role='owner')]);scan=Scan(org_id=a.id,status='completed',result=json.dumps(analyze({'app.py':'def broken(\n'})));db.add(scan);db.commit()
   counts={table.name:db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}
   data={'started':time.time(),'org_id':a.id,'scan_id':scan.id,'counts':counts};manifest.write_text(json.dumps(data))
  print('Synthetic backup fixture ready; database archive must remain in temporary CI storage')
 else:
  data=json.loads(manifest.read_text())
  with db_factory() as db:
   counts={table.name:db.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables}
  assert counts==data['counts'],'Restored row counts differ'
  app=create_app(url,mode='development')
  with TestClient(app) as client:
   assert client.post('/api/auth/login',json={'email':'restore-owner@example.test','password':password}).status_code==200
   report=client.get(f'/api/orgs/{data["org_id"]}/scans/{data["scan_id"]}/report').json()
   assert report['result']['findings'][0]['category']=='syntax'
  with TestClient(app) as other:
   assert other.post('/api/auth/login',json={'email':'restore-other@example.test','password':password}).status_code==200
   assert other.get(f'/api/orgs/{data["org_id"]}/scans/{data["scan_id"]}/report').status_code==404
  summary.write_text(json.dumps({'row_counts_match':True,'restored_login':True,'restored_report':True,'restored_tenant_isolation':True,'roundtrip_seconds':round(time.time()-data['started'],3),'scope':'Synthetic disposable PostgreSQL16 CI database; not a Neon point-in-time restore drill'},indent=2))
  print('Restore checks passed: row counts, login, report evidence and two-user isolation')
finally:engine.dispose()
