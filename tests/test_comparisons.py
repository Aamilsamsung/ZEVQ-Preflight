import copy,json
import pytest
from test_api import env,login
from app.comparisons import compare_results
from app.db import Scan


def result(findings,**extra):
    return dict(engine_version='1',findings=findings,coverage={},risk_score=20,**extra)


def test_deterministic_groups_preserve_evidence():
    a={'id':'a','severity':'high','evidence':{'line':1}};b={'id':'b','severity':'low'};c={'id':'c','severity':'medium'}
    before=result([a,b,{'id':'stable','severity':'low'}]);after=result([{**a,'severity':'medium'},c,{'id':'stable','severity':'low'}]);snapshot=copy.deepcopy((before,after))
    data=compare_results(before,after)
    assert data['counts']==dict(added=1,not_observed=1,changed=1,unchanged=1,unmatched_baseline=0,unmatched_proposed=0)
    assert data['changed'][0]['changed_fields']==['severity'] and data['not_observed']==[b]
    assert (before,after)==snapshot
    assert data==compare_results(before,after)


def test_ambiguous_and_missing_ids_never_imply_new_or_fixed():
    data=compare_results(result([{'id':'duplicate'},{'id':'duplicate'}, {'message':'legacy'}]),result([{'id':'duplicate'}]))
    assert data['counts']==dict(added=0,not_observed=0,changed=0,unchanged=0,unmatched_baseline=3,unmatched_proposed=1)
    assert data['warnings']


def test_engine_and_coverage_warnings():
    a=result([]);b=result([]);b.update(engine_version='2',coverage={'skipped':['large.py'],'route_removal_checks_complete':False})
    data=compare_results(a,b);assert len(data['warnings'])==3
    assert 'not mean fixed' in data['limitations']


def seed(app,org,**extra):
    with app.state.db() as db:
        scan=Scan(org_id=org,status='completed',repository='OpenAPI contract',result=json.dumps(result([{'id':'known','severity':'high'}])))
        for k,v in extra.items():setattr(scan,k,v)
        db.add(scan);db.commit();return scan.id


def test_comparison_scoped_read_only_and_source_warnings(env):
    app,c,(org,foreign,*_)=env;old=seed(app,org);new=seed(app,org);secret=seed(app,foreign)
    root=f'/api/orgs/{org}/comparisons';params=dict(baseline_id=old,proposed_id=new)
    assert c.get(root,params=params).status_code==401
    login(c,'viewer@example.test');r=c.get(root,params=params);assert r.status_code==200
    assert r.json()['counts']['unchanged']==1 and any('shared source identity' in w for w in r.json()['warnings'])
    for a,b in [(old,secret),(secret,new)]:assert c.get(root,params=dict(baseline_id=a,proposed_id=b)).status_code==404
    assert c.get(f'/api/orgs/{foreign}/comparisons',params=params).status_code==404
    assert c.get(root,params=dict(baseline_id=old,proposed_id='missing')).status_code==404


@pytest.mark.parametrize('variation,expected',[('same',422),('pending',409),('source',422)])
def test_invalid_comparison_pairs(env,variation,expected):
    app,c,(org,*_)=env;login(c);old=seed(app,org)
    new=old if variation=='same' else seed(app,org,**({'status':'queued'} if variation=='pending' else {'repository':'different/project'}))
    assert c.get(f'/api/orgs/{org}/comparisons',params=dict(baseline_id=old,proposed_id=new)).status_code==expected
