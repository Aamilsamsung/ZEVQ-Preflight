"""Prepare trusted previous application source with current additive migration history.

An old Render artifact lacks revision0006 and cannot safely run its migration
startup against schema0006. This builder never connects to any database or deploys.
"""
import argparse
import hashlib
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

PREVIOUS_APP = '93ec40a16e0dbeeb7ea696de6291ceacb4060b73'


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise FileExistsError('Use a new empty destination; existing work is never replaced')
    migration = source / 'migrations/versions/0006_public_onboarding.py'
    if not migration.is_file():
        raise RuntimeError('Current migration history through0006 is required')
    archive = subprocess.check_output(['git', '-C', str(source), 'archive', '--format=tar', PREVIOUS_APP])
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(destination, filter='data')
    # Preserve all currently understood revisions, not only the final version.
    # Never substitute a schema downgrade for an application rollback.
    shutil.copytree(source / 'migrations', destination / 'migrations', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ['alembic.ini', 'requirements.txt']:
        shutil.copy2(source / name, destination / name)
    manifest = {
        'previous_application_commit': PREVIOUS_APP,
        'migration_history_revision': '0006',
        'migration_0006_sha256': hashlib.sha256(migration.read_bytes()).hexdigest(),
        'requirements_sha256': hashlib.sha256((source / 'requirements.txt').read_bytes()).hexdigest(),
        'database_or_deployment_changes': False,
        'scope': 'Prepared source bundle only; test and review before any deployment. Historical Render artifact rollback is not equivalent.'
    }
    (destination / 'ROLLBACK_BUNDLE_MANIFEST.json').write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    result = prepare(Path(__file__).resolve().parents[1], args.destination)
    print(json.dumps(result))
