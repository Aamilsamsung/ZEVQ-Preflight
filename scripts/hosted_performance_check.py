"""Opt-in bounded warm-request measurements; only synthetic QA finding decisions."""
import json,os,time
from pathlib import Path
import httpx
if os.getenv('PREFLIGHT_HOSTED_QA')!='1':raise SystemExit('Explicit hosted QA opt-in required')
phase=os.getenv('PREFLIGHT_PERF_PHASE','before')
if phase not in ('before','after'):raise SystemExit('Unknown measurement phase')
out=Path('artifacts/hosted-isolation');fixture=json.loads((out/'credentials.json').read_text());user=fixture['accounts'][0]
samples=int(os.getenv('PREFLIGHT_PERF_SAMPLES','3'))
if not 1<=samples<=30:raise SystemExit('Use1–30 bounded sequential samples')
rows=[];trace_steps=[];trace_started={}
def trace(name,info):
 key,_,state=name.rpartition('.')
 if state=='started':trace_started[key]=time.perf_counter()
 elif state in ('complete','failed') and key in trace_started:trace_steps.append({'phase':key,'ms':round((time.perf_counter()-trace_started.pop(key))*1000,3)})
# Trace event metadata is deliberately ignored: no headers, URLs, credentials or payloads are recorded.
with httpx.Client(base_url='https://zevq-preflight-staging.onrender.com',timeout=40) as client:
 try:
  start=time.perf_counter();r=client.post('/api/auth/login',json={'email':user['email'],'password':user['password']},extensions={'trace':trace});assert r.status_code==200
  rows.append(dict(operation='login',seconds=round(time.perf_counter()-start,3),client_trace=list(trace_steps)))
  client.headers['X-CSRF-Token']=client.get('/api/auth/me').json()['csrf_token']
  sid=next(x['evidence']['scan_id'] for x in json.loads((out/'review-results.json').read_text()) if x['feature']=='Controlled breaking-change scan completes')
  root='/api/orgs/'+fixture['orgs'][0]['id']+'/scans/'+sid
  for iteration in range(samples):
   trace_steps.clear();start=time.perf_counter();r=client.get(root,extensions={'trace':trace});assert r.status_code==200;report=r.json()
   rows.append(dict(operation='report',iteration=iteration,seconds=round(time.perf_counter()-start,3),server_timing=r.headers.get('server-timing'),client_trace=list(trace_steps)))
   fid=report['result']['findings'][0]['id'];version=report['reviews'].get(fid,{}).get('version',0)
   trace_steps.clear();start=time.perf_counter();r=client.put(root+'/findings/'+fid+'/review',extensions={'trace':trace},json=dict(status='acknowledged',reason='Synthetic controlled performance measurement',expires_at=None,expected_version=version));assert r.status_code==200
   rows.append(dict(operation='review_save',iteration=iteration,seconds=round(time.perf_counter()-start,3),server_timing=r.headers.get('server-timing'),client_trace=list(trace_steps)))
   (out/('performance-'+phase+'.json')).write_text(json.dumps(dict(phase=phase,scope=str(samples)+' sequential report/save pairs on the same synthetic finding and reused HTTPS client; no load test or guaranteed cold-start equivalence',rows=rows),indent=2))
 finally:
  try:client.post('/api/auth/logout')
  except httpx.HTTPError:pass
print(json.dumps({'phase':phase,'requests_measured':len(rows)}))
