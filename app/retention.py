"""Owner-confirmed cleanup of old terminal scans; reviewed scans are always preserved."""
import json,time
from fastapi import HTTPException
from sqlalchemy import select,delete,exists
from .db import Organization,Scan,FindingReview,FindingReviewEvent,RetentionPolicy,CleanupRun,Audit

TERMINAL=('completed','failed','cancelled')

def policy_dict(row):
    return {'days':row.days if row else None,'version':row.version if row else 0,'scheduled_cleanup':False,'preserve_reviewed_scans':True,'batch_limit':100,'preview_expiry_seconds':600}

def run_dict(row):
    return {**{k:getattr(row,k) for k in ('id','status','created_at','expires_at','cutoff','deleted_count','preserved_count','reason')},'scan_ids':json.loads(row.scan_ids),'policy_version':row.policy_version}

def lock_org(db,org):db.scalar(select(Organization).where(Organization.id==org).with_for_update())

def set_policy(db,org,actor,days,version):
    lock_org(db,org);row=db.get(RetentionPolicy,org)
    if version!=(row.version if row else 0):raise HTTPException(409,'Policy changed; reload settings')
    if row:row.days=days;row.version+=1;row.updated_at=time.time()
    else:row=RetentionPolicy(org_id=org,days=days,version=1,updated_at=time.time());db.add(row)
    db.add(Audit(org_id=org,actor_id=actor,action='retention.policy_changed'));db.commit();return policy_dict(row)

def preview(db,org,actor):
    lock_org(db,org);policy=db.get(RetentionPolicy,org)
    if not policy or policy.days is None:raise HTTPException(409,'Configure a manual retention age first')
    now=time.time();cutoff=now-policy.days*86400
    ids=list(db.scalars(select(Scan.id).where(Scan.org_id==org,Scan.status.in_(TERMINAL),Scan.updated_at<cutoff,
        ~exists(select(FindingReview.scan_id).where(FindingReview.scan_id==Scan.id)),
        ~exists(select(FindingReviewEvent.scan_id).where(FindingReviewEvent.scan_id==Scan.id))).order_by(Scan.updated_at,Scan.id).limit(100)))
    run=CleanupRun(org_id=org,actor_id=actor,policy_version=policy.version,cutoff=cutoff,scan_ids=json.dumps(ids),created_at=now,expires_at=now+600,status='preview',deleted_count=0,preserved_count=0,reason='')
    db.add(run);db.add(Audit(org_id=org,actor_id=actor,action='retention.preview'));db.commit();return run_dict(run)

def apply(db,org,actor,run_id,reason):
    lock_org(db,org);run=db.scalar(select(CleanupRun).where(CleanupRun.id==run_id,CleanupRun.org_id==org,CleanupRun.actor_id==actor).with_for_update())
    if not run:raise HTTPException(404,'Cleanup preview not found')
    if run.status=='applied':return run_dict(run)
    if run.expires_at<=time.time():raise HTTPException(409,'Preview expired; run a new dry run')
    policy=db.get(RetentionPolicy,org)
    if not policy or policy.days is None or policy.version!=run.policy_version:raise HTTPException(409,'Policy changed; run a new dry run')
    ids=json.loads(run.scan_ids)
    # Review writes acquire these same scan locks. Check review data in a fresh statement after acquiring locks.
    locked=list(db.scalars(select(Scan.id).where(Scan.org_id==org,Scan.id.in_(ids),Scan.status.in_(TERMINAL),Scan.updated_at<run.cutoff).with_for_update()))
    protected=set(db.scalars(select(FindingReview.scan_id).where(FindingReview.scan_id.in_(locked)).union(select(FindingReviewEvent.scan_id).where(FindingReviewEvent.scan_id.in_(locked)))))
    eligible=[sid for sid in locked if sid not in protected]
    run.deleted_count=db.execute(delete(Scan).where(Scan.org_id==org,Scan.id.in_(eligible))).rowcount
    run.preserved_count=len(ids)-run.deleted_count;run.status='applied';run.reason=reason
    db.add(Audit(org_id=org,actor_id=actor,action='retention.applied:'+run.id+':'+str(run.deleted_count)));db.commit();return run_dict(run)
