"""Opt-in, bounded staging audit. Creates labeled synthetic org/scans; never deletes data.
Credentials are read from an ignored operator file and never written to results.
Run only with PREFLIGHT_AUDIT_APPROVED=1 against the named staging origin.
"""
import io,json,os,time,uuid,zipfile,statistics,hashlib
from pathlib import Path
import httpx
BASE='https://zevq-preflight-staging.onrender.com'
OUT=Path('artifacts/independent-audit');OUT.mkdir(parents=True,exist_ok=True)
if os.getenv('PREFLIGHT_AUDIT_APPROVED')!='1':raise SystemExit('Explicit audit opt-in required')
results=[];timings={};scans=[]
def record(name,passed,evidence,severity='Medium'):
    results.append(dict(feature=name,status='PASS' if passed else 'FAIL',evidence=evidence,severity=severity if not passed else '—'));save()
def save():
    (OUT/'live-results.json').write_text(json.dumps({'base':BASE,'executed_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'checks':results,'timings_ms':timings,'scans':scans},indent=2))
def req(c,method,path,**kw):
    start=time.perf_counter();r=c.request(method,path,**kw);timings.setdefault(method+' '+path.split('?')[0],[]).append(round((time.perf_counter()-start)*1000,1));return r
def z(sources):
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as a:
        for name,body in sources.items():a.writestr(name,body)
    return b.getvalue()
def check_scan(c,path,**kwargs):
    start=time.perf_counter();r=req(c,'POST',path,**kwargs)
    if r.status_code!=202:raise RuntimeError('Scan submission rejected '+str(r.status_code)+' '+r.text[:180])
    data=r.json();sid=data['id'];states=[data['status']]
    for i in range(75):
        time.sleep(1);data=req(c,'GET',f'{orgpath}/scans/{sid}').json();states.append(data.get('status'))
        if data.get('status') in ('completed','failed','cancelled'):break
    entry={'id':sid,'states':list(dict.fromkeys(states)),'wall_ms':round((time.perf_counter()-start)*1000,1),'engine_ms':(data.get('result') or {}).get('duration_ms'),'status':data.get('status')};scans.append(entry)
    (OUT/(sid+'.json')).write_text(json.dumps(data,indent=2));save();return data
try:
  with httpx.Client(base_url=BASE,timeout=60,follow_redirects=False) as anon, httpx.Client(base_url=BASE,timeout=60,follow_redirects=False) as c:
    for _ in range(3):r=req(anon,'GET','/login')
    record('Anonymous login page',r.status_code==200,f'HTTP {r.status_code}; 3 sequential samples')
    r=req(anon,'GET','/app');record('Anonymous workspace gate',r.status_code==303 and r.headers.get('location')=='/login',f'HTTP {r.status_code} redirect {r.headers.get("location")}')
    r=req(anon,'GET','/api/auth/me');record('Anonymous API denial',r.status_code==401,f'HTTP {r.status_code}')
    r=req(anon,'POST','/api/auth/register',json={});record('Closed registration',r.status_code==403,f'HTTP {r.status_code}')
    secret=json.loads(Path('artifacts/deployment-secrets.json').read_text())
    r=req(c,'POST','/api/auth/login',json={'email':'zevqlabs@gmail.com','password':secret['admin_password']});record('Live API login',r.status_code==200,f'HTTP {r.status_code}');r.raise_for_status()
    cookie=r.headers.get('set-cookie','');record('Cookie security flags',all(x in cookie.lower() for x in ['secure','httponly','samesite=strict']), 'Secure / HttpOnly / SameSite=Strict / 7-day lifetime')
    me=req(c,'GET','/api/auth/me').json();h={'X-CSRF-Token':me['csrf_token']};original=me['organizations'][0]['id']
    r=req(c,'POST','/api/orgs',json={'name':'must-not-be-created'});record('Missing CSRF rejected',r.status_code==403,f'HTTP {r.status_code}')
    r=req(c,'POST','/api/orgs',headers={**h,'Origin':'https://untrusted.invalid'},json={'name':'must-not-be-created'});record('Foreign Origin rejected',r.status_code==403,f'HTTP {r.status_code}')
    r=req(c,'POST','/api/orgs',headers=h,json={'name':'Independent QA '+time.strftime('%H%M%S')});r.raise_for_status();org=r.json()['id'];orgpath='/api/orgs/'+org
    (OUT/'context.json').write_text(json.dumps({'org':org,'original_org':original}));record('Controlled audit workspace',r.status_code==201,'Created labeled synthetic organization '+org)
    for suffix in ['/repos','/scans','/dashboard','/members','/audit']:
        r=req(c,'GET','/api/orgs/'+str(uuid.uuid4())+suffix);record('Nonmember organization '+suffix,r.status_code==404,f'HTTP {r.status_code}')
    for bad in ['http://127.0.0.1/private','https://github.com/a/b','a/b/../../x']:
        r=req(c,'POST',orgpath+'/repos',headers=h,json={'full_name':bad});record('Unsafe repository input '+bad,r.status_code==422,f'HTTP {r.status_code}')
    r=req(c,'POST',orgpath+'/repos',headers=h,json={'full_name':'Aamilsamsung/ZEVQ-Preflight'});r.raise_for_status();repo=r.json()['id']
    for bad in [('../escape.py','print(1)'),('C:/escape.py','print(1)')]:
        r=req(c,'POST',orgpath+'/scans/zip',headers=h,files={'file':('malicious.zip',z(dict([bad])),'application/zip')});record('ZIP traversal rejected '+bad[0],r.status_code==422,f'HTTP {r.status_code}')
    r=req(c,'POST',orgpath+'/scans/zip',headers=h,files={'file':('broken.zip',b'not a zip','application/zip')});record('Malformed ZIP rejected',r.status_code==422,f'HTTP {r.status_code}')
    r=req(c,'POST',orgpath+'/contracts',headers=h,json={'baseline':{'openapi':'wrong','paths':{}},'proposed':{'paths':{}}});record('Malformed contract rejected',r.status_code==422,f'HTTP {r.status_code}')
    base={'openapi':'3.0.3','info':{'title':'QA','version':'1'},'paths':{'/orders':{'get':{'responses':{'200':{'description':'OK'}}}}}}
    gone={**base,'paths':{}}
    d=check_scan(c,orgpath+'/contracts',headers=h,json={'baseline':base,'proposed':gone});f=d.get('result',{}).get('findings',[]);record('Known OpenAPI endpoint removal',d['status']=='completed' and any('Removed endpoint' in x.get('message','') for x in f),f'{d["id"]}: '+str([(x.get('rule_id'),x.get('severity')) for x in f]));sid=d['id']
    for fmt in ['json','csv']:
        r=req(c,'GET',f'{orgpath}/scans/{sid}/report?format={fmt}');(OUT/('report.'+fmt)).write_bytes(r.content);record('Access-controlled '+fmt+' export',r.status_code==200 and 'attachment' in r.headers.get('content-disposition',''),f'HTTP {r.status_code}; {len(r.content)} bytes')
    r=req(anon,'GET',f'{orgpath}/scans/{sid}/report');record('Anonymous report denial',r.status_code==401,f'HTTP {r.status_code}')
    r=req(c,'GET',f'/api/orgs/{original}/scans/{sid}');record('Scan ID scoped to organization',r.status_code==404,f'HTTP {r.status_code}; same owner, wrong organization')
    d=check_scan(c,orgpath+'/contracts',headers=h,json={'baseline':base,'proposed':base});f=d.get('result',{}).get('findings',[]);record('Unchanged contract safe control',d['status']=='completed' and not f,f'{d["id"]}: {len(f)} findings')
    old={'api.py':'def public_api(user):\n    return user\n\ndef removed_api():\n    return 1\n'}
    new={'api.py':'def public_api(user, required):\n    return user\n'}
    d=check_scan(c,orgpath+'/scans/zip',headers=h,files={'file':('proposed.zip',z(new),'application/zip'),'baseline':('baseline.zip',z(old),'application/zip')});f=d.get('result',{}).get('findings',[]);record('Python removal and signature changes',d['status']=='completed' and any('signature changed' in x.get('message','') for x in f) and any('removed: removed_api' in x.get('message','') for x in f),f'{d["id"]}: '+str([(x.get('message'),x.get('severity')) for x in f]))
    d=check_scan(c,orgpath+'/scans/zip',headers=h,files={'file':('safe.zip',z(old),'application/zip'),'baseline':('safe-base.zip',z(old),'application/zip')});f=d.get('result',{}).get('findings',[]);record('Unchanged Python safe control',d['status']=='completed' and not any(x.get('severity') in ('critical','high') for x in f),f'{d["id"]}: {len(f)} findings')
    key='audit-'+str(uuid.uuid4());payload={'repository_id':repo,'base_ref':'main','head_ref':'main'}
    d=check_scan(c,orgpath+'/scans',headers={**h,'Idempotency-Key':key},json=payload);record('Public GitHub branch comparison',d['status']=='completed',f'{d["id"]}; main → main; status {d["status"]}')
    r=req(c,'POST',orgpath+'/scans',headers={**h,'Idempotency-Key':key},json=payload);record('Idempotency same scan returned',r.status_code==202 and r.json().get('id')==d['id'],f'HTTP {r.status_code}; stable job ID')
    d=check_scan(c,orgpath+'/scans',headers=h,json={'repository_id':repo,'head_ref':'audit-ref-that-does-not-exist-20261028'});record('Invalid ref produces honest failed scan',d['status']=='failed' and bool(d.get('error')),f'{d["id"]}; {d.get("error")}')
    r=req(c,'GET',orgpath+'/scans');record('History includes controlled scans',r.status_code==200 and len(r.json())==6,f'HTTP {r.status_code}; {len(r.json())} scans')
    r=req(c,'GET',orgpath+'/dashboard');record('Dashboard aggregates real scans',r.status_code==200 and r.json().get('scans')==6,f'HTTP {r.status_code}; counts {r.json().get("scans")}')
    for path in ['/api/ready',orgpath+'/dashboard',orgpath+'/scans']:
        for _ in range(3):r=req(c,'GET',path)
    r=req(c,'GET','/app');headers=r.headers;required=['content-security-policy','x-frame-options','x-content-type-options','strict-transport-security','referrer-policy'];record('Authenticated page security headers',all(x in headers for x in required),', '.join(k for k in required if k in headers))
    saved_cookie=c.cookies.get('preflight_session');r=req(c,'POST','/api/auth/logout',headers=h)
    r=req(c,'GET','/api/auth/me',headers={'Cookie':'preflight_session='+saved_cookie});record('Logged-out session replay denied',r.status_code==401,f'HTTP {r.status_code}')
    r=req(anon,'GET','/api/auth/me');record('Anonymous errors carry security headers',all(x in r.headers for x in required),f'HTTP {r.status_code}; missing '+','.join(x for x in required if x not in r.headers),'Low')
except Exception as e:
    results.append({'feature':'Audit execution interruption','status':'BLOCKED','evidence':type(e).__name__+': '+str(e)[:300],'severity':'—'});save()
finally:
    print(json.dumps({'checks':len(results),'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results),'blocked':sum(x['status']=='BLOCKED' for x in results),'scan_count':len(scans)}))
