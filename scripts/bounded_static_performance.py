"""Three trusted contract fixtures, two local static workers; never a hosted load test."""
import json
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlalchemy import select
from app.db import Base, Scan, Organization, make_engine, factory
from app.worker import claim, execute


def main():
    with tempfile.TemporaryDirectory(prefix='preflight-perf-') as directory:
        engine=make_engine('sqlite:///'+str(Path(directory)/'synthetic.db'));Base.metadata.create_all(engine);db_factory=factory(engine)
        with db_factory() as db:
            org=Organization(name='Synthetic performance fixture');db.add(org);db.flush()
            pair={'baseline':{'openapi':'3.0.3','paths':{'/fixture':{'get':{'responses':{'200':{'description':'ok'}}}}}},'proposed':{'openapi':'3.0.3','paths':{}}}
            jobs=[Scan(org_id=org.id,status='queued',payload=json.dumps({'contracts':pair})) for _ in range(3)];db.add_all(jobs);db.commit();ids=[j.id for j in jobs]
        # Claim serially, then execute a bounded pair concurrently. SQLite lacks
        # PostgreSQL SKIP LOCKED semantics, which are tested separately in CI.
        claims=[claim(db_factory) for _ in ids];assert all(claims)
        started=time.perf_counter()
        def run(job):execute(db_factory,*job)
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,claims))
        with db_factory() as db:
            rows=db.scalars(select(Scan).where(Scan.id.in_(ids))).all()
            assert len(rows)==3 and all(r.status=='completed' for r in rows)
            results=[json.loads(r.result) for r in rows];assert all(len(r['findings'])==1 and r['simulation']['status']=='not-executed' for r in results)
        durations=sorted(r['duration_ms'] for r in results)
        result={'scope':'Disposable local SQLite, three known OpenAPI fixtures, two threads running static analysis; not customer code, hosted throughput, or a leak test','jobs':3,'concurrency':2,'passed':3,'execution_ms':durations,'p50_ms':durations[1],'p95_ms':durations[-1],'batch_wall_ms':round((time.perf_counter()-started)*1000,2)}
        Path('artifacts/bounded-static-performance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));engine.dispose()

if __name__=='__main__':main()
