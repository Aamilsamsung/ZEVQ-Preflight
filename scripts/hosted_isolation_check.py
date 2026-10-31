"""Bounded staging checks using previously provisioned, synthetic isolated accounts.
Requires explicit opt-in. Never provisions users, sends emails or deletes accounts.
"""
import json,os,time
from pathlib import Path
import httpx
if os.getenv('PREFLIGHT_HOSTED_QA')!='1':raise SystemExit('Explicit hosted QA opt-in required')
p=Path('artifacts/hosted-isolation');fixture=json.loads((p/'credentials.json').read_text());results=[]
def record(name,ok,evidence):
 results.append({'feature':name,'status':'PASS' if ok else 'FAIL','evidence':evidence});(p/'results.json').write_text(json.dumps(results,indent=2))
clients=[]
try:
 for user in fixture['accounts']:
  c=httpx.Client(base_url='https://zevq-preflight-staging.onrender.com',timeout=60);clients.append(c)
  r=c.post('/api/auth/login',json={'email':user['email'],'password':user['password']});assert r.status_code==200
  me=c.get('/api/auth/me').json();c.headers['X-CSRF-Token']=me['csrf_token']
 owner,viewer,outsider=clients;a,b=[o['id'] for o in fixture['orgs']];root='/api/orgs/'+a
 for client,foreign in [(owner,b),(outsider,a),(viewer,b)]:
  for suffix in ['/repos','/scans','/dashboard','/members','/audit']:
   r=client.get('/api/orgs/'+foreign+suffix);record('Cross-user '+suffix,r.status_code==404,'HTTP '+str(r.status_code))
 r=viewer.post(root+'/repos',json={'full_name':'Aamilsamsung/ZEVQ-Preflight'});record('Viewer repository writes denied',r.status_code==403,'HTTP '+str(r.status_code))
 record('Viewer audit denied',viewer.get(root+'/audit').status_code==403,'Viewer cannot read privileged audit records')
 record('Viewer cannot add members',viewer.post(root+'/members',json={'email':fixture['accounts'][2]['email'],'role':'administrator'}).status_code==403,'No membership granted')
 r=owner.post(root+'/repos',json={'full_name':'Aamilsamsung/ZEVQ-Preflight'});record('Owner connects permitted repository',r.status_code in [201,409],'HTTP '+str(r.status_code))
 spec={'openapi':'3.0.3','paths':{}}
 r=owner.post(root+'/contracts',json={'baseline':spec,'proposed':spec});assert r.status_code==202;sid=r.json()['id']
 for _ in range(60):
  time.sleep(1);scan=owner.get(root+'/scans/'+sid).json()
  if scan['status'] in ['completed','failed']:break
 record('Controlled owner scan completes',scan['status']=='completed',sid)
 record('Foreign user report denied',outsider.get(root+'/scans/'+sid+'/report').status_code==404,'HTTP404 for existing private report')
 record('Viewer can read own-organization report',viewer.get(root+'/scans/'+sid+'/report').status_code==200,'Authorized read only')
 record('Viewer cannot cancel scans',viewer.post(root+'/scans/'+sid+'/cancel').status_code==403,'Role enforced before job mutation')
 # New controls are tested only after their deployment, by explicit second opt-in.
 if os.getenv('PREFLIGHT_TEST_ACCOUNT_CONTROLS')=='1':
  target=fixture['accounts'][1]['id']
  record('Viewer cannot self-promote',viewer.patch(root+'/members/'+target,json={'role':'administrator'}).status_code==403,'No privilege escalation')
  r=owner.patch(root+'/members/'+target,json={'role':'developer'});record('Owner grants developer in synthetic org',r.status_code==200,'HTTP '+str(r.status_code))
  r=viewer.post(root+'/repos',json={'full_name':'qa-isolation/synthetic'});record('Developer write now permitted',r.status_code in [201,409],'HTTP '+str(r.status_code))
  record('Owner demotes to viewer',owner.patch(root+'/members/'+target,json={'role':'viewer'}).status_code==200,'Role changed')
  record('Demotion takes effect on existing session',viewer.post(root+'/repos',json={'full_name':'qa-isolation/denied'}).status_code==403,'No logout/relogin needed')
  user=fixture['accounts'][1];second=httpx.Client(base_url=viewer.base_url,timeout=60);clients.append(second);assert second.post('/api/auth/login',json={'email':user['email'],'password':user['password']}).status_code==200
  import secrets
  password=secrets.token_urlsafe(36)
  r=viewer.post('/api/auth/password',json={'current_password':user['password'],'new_password':password});record('Synthetic password change succeeds',r.status_code==200,'All sessions must reauthenticate')
  if r.status_code==200:
   record('Other synthetic session revoked',second.get('/api/auth/me').status_code==401,'HTTP401')
   user['password']=password;user.pop('csrf',None);(p/'credentials.json').write_text(json.dumps(fixture));(p/'credentials.json').chmod(0o600)
   r=second.post('/api/auth/login',json={'email':user['email'],'password':password});record('New password authenticates',r.status_code==200,'HTTP '+str(r.status_code))
finally:
 for c in clients:
  try:
   me=c.get('/api/auth/me')
   if me.status_code==200:c.post('/api/auth/logout',headers={'X-CSRF-Token':me.json()['csrf_token']})
  except httpx.HTTPError:pass
  c.close()
 print(json.dumps({'checks':len(results),'passed':sum(r['status']=='PASS' for r in results),'failed':sum(r['status']=='FAIL' for r in results)}))
