import json
import logging
import time
import pytest
from app.db import Base, make_engine, factory, Organization, Scan
from app.worker import claim, execute, process_one, recover, LEASE_SECONDS

@pytest.fixture
def queue(tmp_path):
    engine = make_engine('sqlite:///' + str(tmp_path / 'worker.db'))
    Base.metadata.create_all(engine)
    db_factory = factory(engine)
    with db_factory() as db:
        org = Organization(name='Worker test'); db.add(org); db.flush(); org_id = org.id; db.commit()
    yield db_factory, org_id
    engine.dispose()

def put(queue, **kwargs):
    db_factory, org_id = queue
    with db_factory() as db:
        scan = Scan(org_id=org_id, **kwargs); db.add(scan); db.commit(); return scan.id

def test_durable_claim_and_static_evidence(queue,caplog):
    db_factory, _ = queue
    scan_id = put(queue, payload=json.dumps({'files': {'api.py': 'def broken(\n'}, 'baseline': None, 'skipped': [{'file':'big.ts','reason':'file-size-limit'}]}))
    job = claim(db_factory)
    assert job[0] == scan_id
    assert claim(db_factory) is None
    with caplog.at_level(logging.INFO,logger='preflight.worker'):execute(db_factory,*job)
    entry=json.loads(next(r.message for r in caplog.records if r.message.startswith('{')))
    assert entry['event']=='scan_finished' and entry['status']=='completed' and entry['queue_wait_ms']>=0
    assert 'api.py' not in json.dumps(entry) and 'broken' not in json.dumps(entry)
    with db_factory() as db:
        scan = db.get(Scan, scan_id)
        assert scan.status == 'completed' and scan.payload is None
        result = json.loads(scan.result)
        assert result['findings'][0]['rule'] == 'PY.SYNTAX'
        assert result['coverage']['skipped'][0]['file'] == 'big.ts'
        assert result['simulation']['status'] == 'not-executed'

def test_cancelled_job_cannot_publish(queue):
    db_factory, _ = queue
    scan_id = put(queue, payload=json.dumps({'files': {'app.py':'x=1'}}))
    job = claim(db_factory)
    with db_factory() as db:
        db.get(Scan, scan_id).status = 'cancelled'; db.commit()
    execute(db_factory, *job)
    with db_factory() as db:
        assert db.get(Scan, scan_id).result is None

def test_stale_lease_recovers_and_eventually_fails(queue):
    db_factory, _ = queue
    scan_id = put(queue, status='running', attempts=1, updated_at=time.time()-LEASE_SECONDS-1)
    recover(db_factory)
    with db_factory() as db:
        scan = db.get(Scan, scan_id); assert scan.status == 'queued'
        scan.status='running'; scan.attempts=3; scan.updated_at=time.time()-LEASE_SECONDS-1; db.commit()
    recover(db_factory)
    with db_factory() as db: assert db.get(Scan, scan_id).status == 'failed'

def test_wrong_lease_cannot_publish(queue):
    db_factory, _ = queue
    scan_id = put(queue, payload=json.dumps({'files': {'app.py':'x=1'}}))
    claim(db_factory)
    execute(db_factory, scan_id, 'obsolete-lease')
    with db_factory() as db: assert db.get(Scan, scan_id).status == 'running'

def test_contract_scan_runs_without_code_execution(queue):
    db_factory, _ = queue
    old={'openapi':'3.0.3','paths':{'/orders':{'get':{'responses':{'200':{'description':'OK'}}}}}}
    new={'openapi':'3.0.3','paths':{}}
    scan_id=put(queue,payload=json.dumps({'contracts':{'baseline':old,'proposed':new}}))
    assert process_one(db_factory, subprocess_mode=False)
    with db_factory() as db:
        result=json.loads(db.get(Scan,scan_id).result)
        assert result['risk_level']=='high'
        assert result['simulation']['status']=='not-executed'

def test_source_never_executed(queue, tmp_path):
    db_factory, _=queue
    sentinel=tmp_path/'executed'
    scan_id=put(queue,payload=json.dumps({'files':{'evil.py':f'open({str(sentinel)!r}, "w").write("bad")'}}))
    process_one(db_factory,subprocess_mode=False)
    assert not sentinel.exists()


def test_job_subprocess_emits_redacted_completion(queue):
    import os,subprocess,sys
    db_factory,_=queue
    scan_id=put(queue,payload=json.dumps({'files':{'private-source.py':'SYNTHETIC_LOG_SECRET = True\n'}}))
    _,lease=claim(db_factory)
    process_env=os.environ.copy();process_env['DATABASE_URL']=str(db_factory.kw['bind'].url)
    run=subprocess.run([sys.executable,'-m','app.worker','--job',scan_id,'--lease',lease],env=process_env,capture_output=True,text=True,timeout=30)
    assert run.returncode==0
    assert 'scan_finished' in run.stderr and '"status": "completed"' in run.stderr
    assert 'queue_wait_ms' in run.stderr and 'SYNTHETIC_LOG_SECRET' not in run.stderr and 'private-source.py' not in run.stderr
