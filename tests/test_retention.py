import json,os,time
import pytest
from sqlalchemy import select,func
from test_api import env,login
from app.db import Scan,FindingReview,FindingReviewEvent,CleanupRun,Audit,Membership,User


def scan(app,org,**kwargs):
    values=dict(org_id=org,status='completed',created_at=time.time()-9*86400,updated_at=time.time()-9*86400,result=json.dumps({'findings':[]}))
    values.update(kwargs)
    with app.state.db() as db:
        s=Scan(**values);db.add(s);db.commit();return s.id


def review(app,sid,history=False):
    with app.state.db() as db:
        model=FindingReviewEvent if history else FindingReview
        db.add(model(scan_id=sid,finding_id='synthetic',version=1,status='acknowledged',reason='Preserve controlled review evidence',actor_id='synthetic',updated_at=time.time()));db.commit()


def configure(c,org,h,version=0,days=7):
    r=c.put(f'/api/orgs/{org}/retention',headers=h,json={'days':days,'expected_version':version});assert r.status_code==200;return r.json()


def apply(c,org,h,run):return c.post(f'/api/orgs/{org}/retention/{run}/apply',headers=h,json={'confirmation':'DELETE UNREVIEWED SCANS','reason':'Controlled disposable test cleanup'})


def test_disabled_default_and_role_scope(env):
    app,c,(org,foreign,*_)=env;h=login(c);root=f'/api/orgs/{org}/retention'
    assert c.get(root).json()['days'] is None
    assert c.post(root+'/preview',headers=h).status_code==409
    assert c.post(f'/api/orgs/{foreign}/retention/preview',headers=h).status_code==404
    login(c,'viewer@example.test');h={'X-CSRF-Token':c.get('/api/auth/me').json()['csrf_token']}
    assert c.get(root).status_code==200
    for role in ('viewer','developer','administrator'):
        with app.state.db() as db:
            user=db.scalar(select(User).where(User.email=='viewer@example.test'));db.get(Membership,(org,user.id)).role=role;db.commit()
        assert c.put(root,headers=h,json={'days':7,'expected_version':0}).status_code==403
        assert c.post(root+'/preview',headers=h).status_code==403
        assert c.get(root+'/runs').status_code==403


def test_preview_never_deletes_and_preserves_reviewed_active_recent_foreign(env):
    app,c,(org,foreign,*_)=env;h=login(c);configure(c,org,h)
    eligible=scan(app,org);reviewed=scan(app,org);review(app,reviewed)
    history=scan(app,org);review(app,history,True)
    preserved=[reviewed,history,scan(app,org,status='running'),scan(app,org,updated_at=time.time()),scan(app,foreign)]
    r=c.post(f'/api/orgs/{org}/retention/preview',headers=h);assert r.status_code==200 and r.json()['scan_ids']==[eligible]
    with app.state.db() as db:assert all(db.get(Scan,sid) for sid in preserved+[eligible])
    done=apply(c,org,h,r.json()['id']);assert done.status_code==200 and done.json()['deleted_count']==1
    assert apply(c,org,h,r.json()['id']).json()==done.json()
    with app.state.db() as db:
        assert db.get(Scan,eligible) is None and all(db.get(Scan,sid) for sid in preserved)
        assert db.scalar(select(func.count()).select_from(Audit).where(Audit.action.startswith('retention.applied:')))==1


def test_review_added_after_preview_is_preserved(env):
    app,c,(org,*_)=env;h=login(c);configure(c,org,h);sid=scan(app,org)
    run=c.post(f'/api/orgs/{org}/retention/preview',headers=h).json();review(app,sid)
    r=apply(c,org,h,run['id']);assert r.status_code==200 and r.json()['deleted_count']==0 and r.json()['preserved_count']==1
    with app.state.db() as db:assert db.get(Scan,sid)


@pytest.mark.parametrize('change',['expired','policy','disabled'])
def test_stale_preview_cannot_delete(env,change):
    app,c,(org,*_)=env;h=login(c);configure(c,org,h);sid=scan(app,org);run=c.post(f'/api/orgs/{org}/retention/preview',headers=h).json()
    if change=='expired':
        with app.state.db() as db:db.get(CleanupRun,run['id']).expires_at=time.time()-1;db.commit()
    else:configure(c,org,h,version=1,days=None if change=='disabled' else 14)
    assert apply(c,org,h,run['id']).status_code==409
    with app.state.db() as db:assert db.get(Scan,sid)


def test_confirmation_csrf_tenant_and_policy_conflicts(env):
    app,c,(org,foreign,*_)=env;h=login(c);configure(c,org,h)
    assert c.put(f'/api/orgs/{org}/retention',headers=h,json={'days':30,'expected_version':0}).status_code==409
    run=c.post(f'/api/orgs/{org}/retention/preview',headers=h).json()
    assert c.post(f'/api/orgs/{org}/retention/{run["id"]}/apply',headers=h,json={'confirmation':'delete','reason':'Controlled cleanup reason'}).status_code==422
    assert c.post(f'/api/orgs/{org}/retention/{run["id"]}/apply',json={'confirmation':'DELETE UNREVIEWED SCANS','reason':'Controlled cleanup reason'}).status_code==403
    assert apply(c,foreign,h,run['id']).status_code==404


def test_preview_is_bounded_to_100(env):
    app,c,(org,*_)=env;h=login(c);configure(c,org,h)
    with app.state.db() as db:
        db.add_all([Scan(org_id=org,status='failed',updated_at=time.time()-9*86400) for _ in range(103)]);db.commit()
    run=c.post(f'/api/orgs/{org}/retention/preview',headers=h).json();assert len(run['scan_ids'])==100
    assert apply(c,org,h,run['id']).json()['deleted_count']==100


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='PostgreSQL row-lock concurrency requires disposable CI database')
def test_concurrent_review_commit_before_cleanup_lock_is_preserved(env):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import event
    app,c,(org,*_)=env;h=login(c);configure(c,org,h);sid=scan(app,org);run=c.post(f'/api/orgs/{org}/retention/preview',headers=h).json()
    waiting=threading.Event()
    def before(conn,cursor,statement,params,context,many):
        if 'FROM scans' in statement and 'FOR UPDATE' in statement:waiting.set()
    with app.state.db() as reviewer:
        reviewer.scalar(select(Scan).where(Scan.id==sid).with_for_update())
        event.listen(app.state.engine,'before_cursor_execute',before)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                task=pool.submit(apply,c,org,h,run['id']);assert waiting.wait(5)
                reviewer.add(FindingReview(scan_id=sid,finding_id='synthetic',version=1,status='acknowledged',reason='Concurrent review must survive cleanup',actor_id='synthetic',updated_at=time.time()));reviewer.commit()
                r=task.result(timeout=10);assert r.status_code==200 and r.json()['deleted_count']==0
        finally:event.remove(app.state.engine,'before_cursor_execute',before)
    with app.state.db() as db:assert db.get(Scan,sid) and db.get(FindingReview,(sid,'synthetic'))
