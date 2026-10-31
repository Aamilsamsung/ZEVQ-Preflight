"""Human decisions annotate immutable analysis; they never rewrite detection results."""
import time
from sqlalchemy import select
from .db import FindingReview

STATUSES={'open','acknowledged','false_positive','suppressed'}
MAX_SUPPRESSION_SECONDS=90*86400


def decision_dict(row,now=None):
    now=time.time() if now is None else now
    data={key:getattr(row,key) for key in ('finding_id','version','status','reason','expires_at','actor_id','updated_at')}
    expired=row.status=='suppressed' and row.expires_at is not None and row.expires_at<=now
    return {**data,'expired':expired,'effective_status':'open' if expired else row.status}


def annotate_scan(db,data):
    rows=db.scalars(select(FindingReview).where(FindingReview.scan_id==data['id'])).all()
    now=time.time();findings=(data.get('result') or {}).get('findings',[])
    ids={f.get('id') for f in findings}
    reviews={r.finding_id:decision_dict(r,now) for r in rows if r.finding_id in ids}
    counts={status:0 for status in STATUSES}
    for f in findings:counts[reviews.get(f.get('id'),{}).get('effective_status','open')]+=1
    data.update(reviews=reviews,review_counts=counts,review_policy='Human decisions annotate this scan only. Original findings and risk score are unchanged. Expired suppressions are treated as open.')
    return data
