"""Optional local wake-up hint. Database job records remain the source of truth."""
import logging
import os
from pathlib import Path


def notify_worker():
    filename = os.getenv('PREFLIGHT_WAKE_FILE')
    if filename:
        try:
            Path(filename).touch()
        except OSError:
            logging.getLogger('preflight').error('worker_wakeup_failed')
