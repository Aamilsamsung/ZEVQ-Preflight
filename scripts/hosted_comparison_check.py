"""Read-only staging comparison checks using existing synthetic QA reports."""
import json,os,time
from pathlib import Path
import httpx
if os.getenv('PREFLIGHT_HOSTED_QA')!='1':raise SystemExit('Explicit hosted QA opt-in required')
out=Path('artifacts/hosted-isolation');fixture=json.loads((out/'credentials.json').read_text());results=[];clients=[]
def record(name,ok,evidence):
 results.append(dict(feature=name,status='PASS' if ok else 'FAIL',evidence=evidence));(out/'comparison-results.json').write_text(json.dumps(results,indent=2))
try:
 for user in fixture['accounts']:
  c=httpx.Client(base_url='https://zevq-preflight-staging.onrender.com',timeout=60);clients.append(c)
  assert c.post('/api/auth/login',json={'email':user['email'],'password':user['password']}).status_code==200
  c.headers['X-CSRF-Token']=c.get('/api/auth/me').json()['csrf_token']
 owner,viewer,outsider=clients;root='/api/orgs/'+fixture['orgs'][0]['id'];scans=owner.get(root+'/scans').json()
 old=next(s for s in scans if s['status']=='completed' and s['repository']=='OpenAPI contract' and s['finding_count']==0)
 new_id=next(x['evidence']['scan_id'] for x in json.loads((out/'review-results.json').read_text()) if x['feature']=='Controlled breaking-change scan completes')
 endpoint=root+'/comparisons';params={'baseline_id':old['id'],'proposed_id':new_id}
 t=time.perf_counter();r=owner.get(endpoint,params=params);elapsed=round(time.perf_counter()-t,3);assert r.status_code==200
 data=r.json();record('Hosted comparison observes known endpoint finding',data['counts']['added']==1 and data['counts']['not_observed']==0,{'http':r.status_code,'seconds':elapsed,'baseline_id':old['id'],'proposed_id':new_id})
 record('Comparison includes identity/coverage limitations',bool(data['warnings']) and 'Not observed does not mean fixed' in data['limitations'],'No claim of a verified fix')
 r=viewer.get(endpoint,params=params);record('Viewer reads authorized comparison',r.status_code==200 and r.json()['counts']==data['counts'],'HTTP200')
 record('Outsider cannot read comparison',outsider.get(endpoint,params=params).status_code==404,'HTTP404')
 record('Foreign organization scope denied',owner.get('/api/orgs/'+fixture['orgs'][1]['id']+'/comparisons',params=params).status_code==404,'HTTP404')
 record('Missing report rejected',owner.get(endpoint,params={**params,'proposed_id':'missing'}).status_code==404,'HTTP404')
 record('Self comparison rejected',owner.get(endpoint,params={**params,'proposed_id':old['id']}).status_code==422,'HTTP422')
 reverse=owner.get(endpoint,params={'baseline_id':new_id,'proposed_id':old['id']}).json();record('Reversed comparison preserves absence uncertainty',reverse['counts']['not_observed']==1 and reverse['counts']['added']==0 and 'Not observed does not mean fixed' in reverse['limitations'],'Finding is not called fixed')
finally:
 for c in clients:
  try:c.post('/api/auth/logout')
  except httpx.HTTPError:pass
  c.close()
 print(json.dumps({'checks':len(results),'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results)}))
 if any(x['status']=='FAIL' for x in results):raise SystemExit(1)
