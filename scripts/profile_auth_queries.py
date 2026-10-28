"""Compare trusted pre-change/current authentication on the disposable local QA database."""
import importlib.util,json,os,subprocess,tempfile,time,statistics
from pathlib import Path
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import event
from app.main import create_app
from app import security
if os.getenv('DATABASE_URL') or os.getenv('PREFLIGHT_MODE','development')!='development':raise SystemExit('Default disposable local database only')
source=subprocess.check_output(['git','show','9e78cde832e0d9213aae6450c5fb7d80f90ff6f4:app/security.py']).decode()
with tempfile.TemporaryDirectory() as directory:
 path=Path(directory)/'baseline.py';path.write_text(source)
 spec=importlib.util.spec_from_file_location('app._trusted_auth_baseline',path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 app=create_app();counts=[];results={}
 def count(*args):counts.append(1)
 creds=json.loads(Path('artifacts/qa-credentials.json').read_text())
 with TestClient(app) as c:
  r=c.post('/api/auth/login',json=creds);assert r.status_code==200
  me=c.get('/api/auth/me').json();org=me['organizations'][0]['id']
  event.listen(app.state.engine,'before_cursor_execute',count)
  try:
   for name,module in [('before',old),('after',security)]:
    samples=[]
    for _ in range(10):
     req=Request({'type':'http','method':'POST','path':'/','app':app,'headers':[(b'cookie',('preflight_session='+c.cookies.get('preflight_session')).encode()),(b'x-csrf-token',me['csrf_token'].encode())]})
     counts.clear();start=time.perf_counter();assert module.has_active_session(req);module.member(req,org)
     samples.append({'queries':len(counts),'ms':round((time.perf_counter()-start)*1000,3)})
    results[name]={'samples':samples,'median_queries':statistics.median(s['queries'] for s in samples),'median_ms':round(statistics.median(s['ms'] for s in samples),3)}
  finally:event.remove(app.state.engine,'before_cursor_execute',count)
  c.post('/api/auth/logout',headers={'X-CSRF-Token':me['csrf_token']})
 Path('artifacts/auth-query-profile.json').write_text(json.dumps({'scope':'10 sequential staging-authentication + membership calls per version on the same disposable SQLite QA database; excludes network, PostgreSQL, scan work and cold starts','baseline_commit':'9e78cde832e0d9213aae6450c5fb7d80f90ff6f4','results':results},indent=2))
 print(json.dumps(results))
