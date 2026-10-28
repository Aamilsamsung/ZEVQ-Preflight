"""Durable static-only jobs. Run as a separate worker service/process.

This is NOT a sandbox for customer tests. It never imports or executes customer code.
"""
import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from sqlalchemy import select, update
from .db import make_engine, factory, Scan, uid
from .analyzer import analyze, Sources
from .contracts import compare_openapi, VERSION
from .github import download

log = logging.getLogger('preflight.worker')
LEASE_SECONDS = 180
MAX_ATTEMPTS = 3


def recover(db_factory):
    now = time.time()
    with db_factory() as db:
        stale = db.scalars(select(Scan).where(Scan.status == 'running', Scan.updated_at < now - LEASE_SECONDS).with_for_update(skip_locked=True)).all()
        for scan in stale:
            scan.status = 'failed' if scan.attempts >= MAX_ATTEMPTS else 'queued'
            scan.error = 'Worker lease expired; retry limit reached' if scan.status == 'failed' else None
            scan.updated_at = now; scan.lease = None
            if scan.status == 'failed': scan.payload = None
        db.commit()


def claim(db_factory):
    recover(db_factory)
    with db_factory() as db:
        scan = db.scalar(select(Scan).where(Scan.status == 'queued').order_by(Scan.created_at).with_for_update(skip_locked=True).limit(1))
        if not scan: return None
        lease = uid()
        updated = db.execute(update(Scan).where(Scan.id == scan.id, Scan.status == 'queued').values(status='running', lease=lease, updated_at=time.time(), attempts=Scan.attempts + 1))
        db.commit()
        return (scan.id, lease) if updated.rowcount else None


async def calculate(scan):
    if scan.payload:
        payload = json.loads(scan.payload)
        if 'contracts' in payload:
            pair = payload['contracts']; findings = compare_openapi(pair['baseline'], pair['proposed'])
            result = analyze({})
            weights = {'critical': 40, 'high': 20, 'medium': 7, 'low': 2, 'info': 0}
            result.update(findings=findings, risk_score=min(100, sum(weights[f['severity']] for f in findings)), risk_level='high' if any(f['severity'] == 'high' for f in findings) else 'medium' if any(f['severity'] == 'medium' for f in findings) else 'low', files_scanned=2)
            result['coverage']['baseline_provided'] = True
            return result
        files = Sources(); files.update(payload['files']); files.skipped = payload.get('skipped', [])
        old = None
        if payload.get('baseline') is not None:
            old = Sources(); old.update(payload['baseline']); old.skipped = payload.get('baseline_skipped', [])
    else:
        repo = 'https://github.com/' + scan.repository
        files = await download(repo, scan.head_ref)
        old = await download(repo, scan.base_ref) if scan.base_ref else None
    result = analyze(files, old)
    result['coverage']['baseline_skipped'] = getattr(old, 'skipped', [])
    result['revision_limitation'] = 'Branch refs identify requested inputs, not immutable commit identities. Use commit SHAs for reproducible GitHub scans.'
    return result


def execute(db_factory, scan_id, lease):
    started = time.monotonic()
    with db_factory() as db:
        scan = db.get(Scan, scan_id)
        if not scan or scan.status != 'running' or scan.lease != lease: return
    try:
        result = asyncio.run(asyncio.wait_for(calculate(scan), timeout=90))
        result['duration_ms'] = round((time.monotonic() - started) * 1000, 2)
        values = dict(status='completed', result=json.dumps(result), error=None)
    except Exception as exc:
        # Do not persist source fragments, credentials, remote response bodies or tracebacks.
        safe = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        values = dict(status='failed', error=safe[:300])
    with db_factory() as db:
        db.execute(update(Scan).where(Scan.id == scan_id, Scan.status == 'running', Scan.lease == lease).values(**values, payload=None, lease=None, updated_at=time.time()))
        db.commit()


def process_one(db_factory, subprocess_mode=True):
    job = claim(db_factory)
    if not job: return False
    scan_id, lease = job
    if not subprocess_mode:
        execute(db_factory, scan_id, lease); return True
    try:
        completed = subprocess.run([sys.executable, '-m', 'app.worker', '--job', scan_id, '--lease', lease], timeout=120, check=False)
        if completed.returncode: raise RuntimeError('Static worker process failed')
    except (subprocess.TimeoutExpired, RuntimeError):
        with db_factory() as db:
            db.execute(update(Scan).where(Scan.id == scan_id, Scan.status == 'running', Scan.lease == lease).values(status='failed', error='Static worker resource/time limit exceeded', payload=None, lease=None, updated_at=time.time()))
            db.commit()
    return True


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--once', action='store_true'); parser.add_argument('--job'); parser.add_argument('--lease'); parser.add_argument('--on-demand', action='store_true')
    args = parser.parse_args()
    if args.job:
        if sys.platform == 'linux':
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
            resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
        execute(factory(make_engine()), args.job, args.lease); return
    logging.basicConfig(level=logging.INFO)
    db_factory = factory(make_engine()); stop = False
    def shutdown(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, shutdown); signal.signal(signal.SIGINT, shutdown)
    # Only the single-instance supervisor enables this mode. A local marker avoids
    # continuously waking a free external database while no scans are pending.
    observed = object()
    draining = False
    recovery_at = time.monotonic() + LEASE_SECONDS + 1
    retry_at = None
    while not stop:
        marker = None
        if args.on_demand:
            filename = os.getenv('PREFLIGHT_WAKE_FILE')
            if not filename:
                raise RuntimeError('--on-demand requires the supervisor wake file')
            try: marker = os.stat(filename).st_mtime_ns
            except FileNotFoundError: pass
            now = time.monotonic()
            recover_due = recovery_at is not None and now >= recovery_at
            retry_due = retry_at is not None and now >= retry_at
            if marker == observed and not draining and not recover_due and not retry_due:
                time.sleep(0.5)
                continue
            observed = marker
            if recover_due: recovery_at = None
            retry_at = None
        try: processed = process_one(db_factory)
        except Exception:
            log.error('worker_database_error'); processed = False; retry_at = time.monotonic() + 15
        draining = processed
        if args.once: break
        if not processed: time.sleep(0.5 if args.on_demand else 2)

if __name__ == '__main__':
    main()
