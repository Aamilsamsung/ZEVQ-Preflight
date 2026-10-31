"""One controlled static job on staging; only existing synthetic QA identity."""
import json,os,time
from pathlib import Path
import httpx
if os.getenv('PREFLIGHT_HOSTED_QA')!='1':raise SystemExit('Explicit hosted QA opt-in required')
out=Path('artifacts/hosted-isolation');fixture=json.loads((out/'credentials.json').read_text());user=fixture['accounts'][0]
with httpx.Client(base_url='https://zevq-preflight-staging.onrender.com',timeout=45) as c:
 try:
  assert c.post('/api/auth/login',json={'email':user['email'],'password':user['password']}).status_code==200
  c.headers['X-CSRF-Token']=c.get('/api/auth/me').json()['csrf_token']
  root='/api/orgs/'+fixture['orgs'][0]['id'];spec={'openapi':'3.0.3','paths':{}};start=time.perf_counter()
  r=c.post(root+'/contracts',json={'baseline':spec,'proposed':spec});assert r.status_code==202;sid=r.json()['id']
  for _ in range(40):
   r=c.get(root+'/scans/'+sid);assert r.status_code==200;scan=r.json()
   if scan['status'] in ('completed','failed'):break
   time.sleep(1)
  result={'scan_id':sid,'status':scan['status'],'elapsed_seconds':round(time.perf_counter()-start,3),'request_id':r.headers.get('x-request-id'),'server_timing':r.headers.get('server-timing'),'worker_log_verified':False,'scope':'One empty OpenAPI static contract comparison; no code execution. Provider log verification is separate.'}
  (out/'job-diagnostics.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));assert scan['status']=='completed'
 finally:
  try:c.post('/api/auth/logout')
  except httpx.HTTPError:pass
