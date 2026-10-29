"""Minimal global operational health for an explicitly authorized external monitor."""
import os
import secrets
import time
from fastapi import HTTPException
from sqlalchemy import select, func
from .db import Scan


def monitor_status(request):
    expected = os.getenv('PREFLIGHT_MONITOR_TOKEN', '')
    supplied = request.headers.get('authorization', '')
    if len(expected) < 32 or not secrets.compare_digest(supplied, 'Bearer ' + expected):
        raise HTTPException(404, 'Endpoint not found')
    now = time.time()
    try:
        with request.app.state.db() as db:
            failures = db.scalar(select(func.count()).select_from(Scan).where(Scan.status == 'failed', Scan.updated_at > now - 900))
            stale = db.scalar(select(func.count()).select_from(Scan).where(Scan.status == 'running', Scan.updated_at < now - 180))
            delayed = db.scalar(select(func.count()).select_from(Scan).where(Scan.status == 'queued', Scan.created_at < now - 300))
    except Exception:
        raise HTTPException(503, 'Operational dependency unavailable') from None
    signals = {'repeated_scan_failures': failures >= 3, 'stale_running_job': stale > 0, 'delayed_queue': delayed > 0}
    return {'status': 'degraded' if any(signals.values()) else 'ok', 'signals': signals,
            'limitations': 'An empty queue is not evidence that a worker is alive. API failures are monitored from probe responses, not all request logs.'}
