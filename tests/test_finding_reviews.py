import csv
import io
import json
import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_api import env,login
from app.db import Scan,FindingReview,FindingReviewEvent,Audit
from app.analyzer import analyze


def fixture_scan(app,org,status='completed'):
    result=analyze({'app.py':'def broken(\n'})
    with app.state.db() as db:
        s=Scan(org_id=org,status=status,result=json.dumps(result));db.add(s);db.commit()
        return s.id,result['findings'][0]['id'],result


def body(status='acknowledged',version=0,**extra):
    return {'status':status,'reason':'Reviewed with the service owner','expected_version':version,'expires_at':None,**extra}


def test_decisions_preserve_analysis_and_export_with_history(env):
    app,c,(org,*_)=env;headers=login(c);sid,fid,result=fixture_scan(app,org)
    root=f'/api/orgs/{org}/scans/{sid}';path=root+f'/findings/{fid}/review'
    first=c.put(path,json=body(reason='=HYPERLINK("https://example.invalid")'),headers=headers)
    assert first.status_code==200 and first.json()['version']==1
    assert c.put(path,json=body('false_positive',1),headers=headers).status_code==200
    data=c.get(root).json();assert data['result']==result
    assert data['reviews'][fid]['effective_status']=='false_positive'
    assert data['review_counts']['false_positive']==1
    history=c.get(path+'s').json();assert [x['version'] for x in history]==[2,1]
    assert history[1]['reason'].startswith('=HYPERLINK')
    exported=c.get(root+'/report').json();assert exported['result']==result and exported['reviews']==data['reviews']
    assert c.put(path,json=body('open',2,reason='=HYPERLINK("https://example.invalid")'),headers=headers).status_code==200
    records=list(csv.DictReader(io.StringIO(c.get(root+'/report?format=csv').text)))
    assert records[0]['review_reason'].startswith("'=HYPERLINK")
    assert records[0]['review_status']=='open'
    with app.state.db() as db:
        assert len(db.scalars(select(FindingReviewEvent).where(FindingReviewEvent.scan_id==sid)).all())==3
        assert db.scalar(select(Audit).where(Audit.action=='finding.open:'+fid))


def test_suppression_expires_without_altering_risk(env):
    app,c,(org,*_)=env;h=login(c);sid,fid,result=fixture_scan(app,org);root=f'/api/orgs/{org}/scans/{sid}'
    r=c.put(root+f'/findings/{fid}/review',headers=h,json=body('suppressed',expires_at=time.time()+3600))
    assert r.status_code==200 and r.json()['effective_status']=='suppressed'
    with app.state.db() as db:
        db.get(FindingReview,(sid,fid)).expires_at=time.time()-1;db.commit()
    data=c.get(root).json()
    assert data['reviews'][fid]['expired'] and data['review_counts']['open']==1
    assert data['reviews'][fid]['status']=='suppressed'
    assert data['result']==result


def test_stale_updates_rejected_without_history_change(env):
    app,c,(org,*_)=env;h=login(c);sid,fid,_=fixture_scan(app,org);root=f'/api/orgs/{org}/scans/{sid}/findings/{fid}'
    assert c.put(root+'/review',json=body(),headers=h).status_code==200
    assert c.put(root+'/review',json=body('false_positive'),headers=h).status_code==409
    assert len(c.get(root+'/reviews').json())==1


def test_viewer_read_only_and_developer_cannot_suppress(env):
    app,c,(org,*_)=env;h=login(c);sid,fid,_=fixture_scan(app,org);root=f'/api/orgs/{org}/scans/{sid}/findings/{fid}'
    viewer=TestClient(app);vh=login(viewer,'viewer@example.test');uid=viewer.get('/api/auth/me').json()['id']
    assert viewer.put(root+'/review',json=body(),headers=vh).status_code==403
    assert viewer.get(root+'/reviews').status_code==200
    assert c.patch(f'/api/orgs/{org}/members/{uid}',json={'role':'developer'},headers=h).status_code==200
    assert viewer.put(root+'/review',json=body('suppressed',expires_at=time.time()+3600),headers=vh).status_code==403
    assert viewer.put(root+'/review',json=body(),headers=vh).status_code==200
    assert c.put(root+'/review',json=body('suppressed',1,expires_at=time.time()+3600),headers=h).status_code==200


def test_reviews_tenant_scope_completed_scan_and_finding_validation(env):
    app,c,(org,other,*_)=env;h=login(c);sid,fid,_=fixture_scan(app,other)
    path=f'/api/orgs/{org}/scans/{sid}/findings/{fid}'
    assert c.put(path+'/review',json=body(),headers=h).status_code==404
    assert c.get(path+'/reviews').status_code==404
    sid,fid,_=fixture_scan(app,org,'running');path=f'/api/orgs/{org}/scans/{sid}/findings/{fid}'
    assert c.put(path+'/review',json=body(),headers=h).status_code==409
    sid,fid,_=fixture_scan(app,org);path=f'/api/orgs/{org}/scans/{sid}/findings/unknown'
    assert c.put(path+'/review',json=body(),headers=h).status_code==404
    assert c.get(path+'/reviews').status_code==404


@pytest.mark.parametrize('changes',[
    {'status':'resolved'}, {'reason':' '*12}, {'status':'suppressed'},
    {'status':'suppressed','expires_at':0}, {'status':'suppressed','expires_at':time.time()+91*86400},
    {'expires_at':time.time()+1000}, {'expected_version':-1},
])
def test_review_validation(env,changes):
    app,c,(org,*_)=env;h=login(c);sid,fid,_=fixture_scan(app,org)
    r=c.put(f'/api/orgs/{org}/scans/{sid}/findings/{fid}/review',headers=h,json={**body(),**changes})
    assert r.status_code==422


def test_validation_never_echoes_password_or_nonfinite_input(env):
    app,c,(org,*_)=env;secret='sensitive-input-marker-'+'x'*260
    r=c.post('/api/auth/login',json={'email':'owner@example.test','password':secret})
    assert r.status_code==422 and secret not in r.text and 'input' not in r.json()['detail'][0]
    h=login(c);sid,fid,_=fixture_scan(app,org)
    payload=json.dumps(body('suppressed')).replace('"expires_at": null','"expires_at": NaN')
    r=c.put(f'/api/orgs/{org}/scans/{sid}/findings/{fid}/review',headers={**h,'Content-Type':'application/json'},content=payload)
    assert r.status_code==422 and 'NaN' not in r.text


def test_review_mutation_requires_csrf(env):
    app,c,(org,*_)=env;login(c);sid,fid,_=fixture_scan(app,org)
    assert c.put(f'/api/orgs/{org}/scans/{sid}/findings/{fid}/review',json=body()).status_code==403


def test_decisions_do_not_carry_to_another_scan(env):
    app,c,(org,*_)=env;h=login(c);first,fid,_=fixture_scan(app,org);second,same_fid,_=fixture_scan(app,org)
    assert fid==same_fid
    assert c.put(f'/api/orgs/{org}/scans/{first}/findings/{fid}/review',headers=h,json=body()).status_code==200
    other=c.get(f'/api/orgs/{org}/scans/{second}').json()
    assert other['reviews']=={} and other['review_counts']['open']==1


@pytest.mark.skipif(not __import__('os').getenv('TEST_DATABASE_URL'),reason='PostgreSQL row-lock concurrency check')
def test_concurrent_decisions_have_one_winner(env):
    from concurrent.futures import ThreadPoolExecutor
    app,_,(org,*_)=env;sid,fid,_=fixture_scan(app,org)
    clients=[TestClient(app),TestClient(app)];headers=[login(c) for c in clients]
    path=f'/api/orgs/{org}/scans/{sid}/findings/{fid}/review'
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda i:clients[i].put(path,json=body(),headers=headers[i]).status_code,range(2)))
    assert sorted(responses)==[200,409]
