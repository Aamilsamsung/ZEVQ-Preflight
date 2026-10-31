"""Single free web instance with a separate static-worker process.

No customer programs are executed. External PostgreSQL remains mandatory in staging.
"""
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def supervise(commands, env=None):
    children = []
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for command in commands:
            children.append(subprocess.Popen(command, env=env, start_new_session=os.name == 'posix'))
        while not stopping:
            if any(child.poll() is not None for child in children):
                # A dead worker must not leave a healthy-looking web-only service behind.
                return 1
            time.sleep(0.5)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                try:
                    if os.name == 'posix': os.killpg(child.pid, signal.SIGTERM)
                    else: child.terminate()
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + 10
        for child in children:
            try:
                child.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                try:
                    if os.name == 'posix': os.killpg(child.pid, signal.SIGKILL)
                    else: child.kill()
                except ProcessLookupError:
                    pass
                child.wait()
        for sig, handler in previous.items(): signal.signal(sig, handler)


def main():
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
    if os.getenv('PREFLIGHT_BOOTSTRAP_EMAIL'):
        subprocess.run([sys.executable, '-m', 'app.bootstrap'], check=True)
    with tempfile.TemporaryDirectory(prefix='preflight-') as directory:
        env = os.environ.copy()
        # Runtime children use the restricted pooled role, not migration credentials.
        for key in ("DATABASE_URL_UNPOOLED", "PREFLIGHT_BOOTSTRAP_PASSWORD", "PREFLIGHT_RUNTIME_PASSWORD"):
            env.pop(key, None)
        env['PREFLIGHT_WAKE_FILE'] = str(Path(directory) / 'jobs.signal')
        commands = [
            [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', os.getenv('PORT', '10000'), '--no-access-log'],
            [sys.executable, '-m', 'app.worker', '--on-demand'],
        ]
        return supervise(commands, env)

if __name__ == '__main__':
    raise SystemExit(main())
