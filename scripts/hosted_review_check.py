"""Bounded, opt-in staging checks using isolated synthetic accounts only."""
import json,os,time
from pathlib import Path
import httpx
if os.getenv('PREFLIGHT_HOSTED_QA')!='1':raise SystemExit('Explicit hosted QA opt-in required')
out=Path('artifacts/hosted-isolation');fixture=json.loads((out/'credentials.json').read_text());results=[];clients=[]
def record(name,ok,evidence):
 results.append(dict(feature=name,status='PASS' if ok else 'FAIL',evidence=evidence));(out/'review-results.json').write_text(json.dumps(results,indent=2))
try:
 for user in fixture['accounts']:
  c=httpx.Client(base_url='https://zevq-preflight-staging.onrender.com',timeout=60);clients.append(c)
  assert c.post('/api/auth/login',json={'email':user['email'],'password':user['password']}).status_code==200
  c.headers['X-CSRF-Token']=c.get('/api/auth/me').json()['csrf_token']
 owner,viewer,outsider=clients;root='/api/orgs/'+fixture['orgs'][0]['id'];start=time.perf_counter()
 spec={'openapi':'3.0.3','paths':{'/synthetic-review-orders':{'get':{'responses':{'200':{'description':'OK'}}}}}}
 r=owner.post(root+'/contracts',json={'baseline':spec,'proposed':{'openapi':'3.0.3','paths':{}}});assert r.status_code==202
 sid=r.json()['id'];path=root+'/scans/'+sid
 for _ in range(60):
  scan=owner.get(path).json()
  if scan['status'] in ['completed','failed']:break
  time.sleep(1)
 record('Controlled breaking-change scan completes',scan['status']=='completed',{'scan_id':sid,'seconds':round(time.perf_counter()-start,3)})
 fid=scan['result']['findings'][0]['id'];endpoint=path+'/findings/'+fid;raw=scan['result']
 body=dict(status='acknowledged',reason='Synthetic hosted review with known removed endpoint',expected_version=0,expires_at=None)
 record('Viewer review write denied',viewer.put(endpoint+'/review',json=body).status_code==403,'HTTP403')
 record('Cross-tenant review write denied',outsider.put(endpoint+'/review',json=body).status_code==404,'HTTP404')
 record('Cross-tenant history denied',outsider.get(endpoint+'/reviews').status_code==404,'HTTP404')
 t=time.perf_counter();r=owner.put(endpoint+'/review',json=body);record('Owner acknowledges finding',r.status_code==200,{'http':r.status_code,'seconds':round(time.perf_counter()-t,3)})
 record('Stale decision rejected',owner.put(endpoint+'/review',json=body).status_code==409,'HTTP409')
 report=viewer.get(path+'/report').json();record('Viewer reads decision with original evidence',report['reviews'][fid]['status']=='acknowledged' and report['result']==raw,'JSON export preserves scanner result')
 csv=owner.get(path+'/report?format=csv');record('CSV contains decision',csv.status_code==200 and 'review_status' in csv.text and body['reason'] in csv.text,'Current review columns exported')
 body.update(status='suppressed',expected_version=1,expires_at=time.time()+5)
 r=owner.put(endpoint+'/review',json=body);record('Owner time-limited suppression',r.status_code==200 and r.json()['effective_status']=='suppressed','Five-second synthetic expiry')
 time.sleep(6)
 report=owner.get(path).json();record('Expired suppression reopens without score changes',report['reviews'][fid]['expired'] and report['reviews'][fid]['effective_status']=='open' and report['result']==raw,'Raw finding and score identical')
 body.update(status='open',expected_version=2,expires_at=None)
 record('Owner explicitly reopens',owner.put(endpoint+'/review',json=body).status_code==200,'HTTP200')
 history=viewer.get(endpoint+'/reviews').json();record('Viewer sees all decision versions',[x['version'] for x in history]==[3,2,1],'Three retained decisions')
 record('Review history pagination',len(owner.get(endpoint+'/reviews?offset=2').json())==1,'Offset2 returns original decision')
finally:
 for c in clients:
  try:c.post('/api/auth/logout')
  except httpx.HTTPError:pass
  c.close()
 print(json.dumps({'checks':len(results),'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results)}))
 if any(x['status']=='FAIL' for x in results):raise SystemExit(1)
