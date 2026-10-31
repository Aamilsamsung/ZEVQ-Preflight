"""Non-destructive application verification on the named isolated Neon snapshot only.

Never imports pytest's destructive database fixtures or migrates/downgrades a DB.
Original business rows are fingerprinted privately and must remain identical.
"""
import hashlib
import json
import os
import secrets
import time
import uuid
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

SNAPSHOT_HOST = 'ep-dark-king-b3w2usjz.c-4.ap-southeast-1.aws.neon.tech'
BRANCH = 'implementation/public-onboarding-20261029'


def snapshot_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme not in ('postgres', 'postgresql', 'postgresql+psycopg')
            or parsed.hostname != SNAPSHOT_HOST or parsed.path != '/neondb'
            or not parsed.username or not parsed.password or parsed.fragment
            or parsed.port not in (None, 5432)):
        raise ValueError('Only the explicitly isolated recovery snapshot endpoint is allowed')
    query = dict(parse_qsl(parsed.query))
    query['sslmode'] = 'verify-full'
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ''))


def concurrency_guard():
    if os.getenv('GITHUB_REPOSITORY') != 'Aamilsamsung/ZEVQ-Preflight':
        raise RuntimeError('Run only in the authorized repository runner')
    request = Request('https://api.github.com/repos/Aamilsamsung/ZEVQ-Preflight/branches/' + BRANCH.replace('/', '%2F'),
                      headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json'})
    with urlopen(request, timeout=15) as response:
        remote = json.load(response)['commit']['sha']
    if remote != os.environ['GITHUB_SHA']:
        raise RuntimeError('Concurrent branch activity detected; stop before database mutation')


def fingerprints(connection, original=None):
    from sqlalchemy import MetaData, Table, select, tuple_
    names = ['users', 'organizations', 'memberships', 'scans', 'sessions', 'repositories',
             'repository_credentials', 'finding_reviews', 'finding_review_events', 'audit_events',
             'email_tokens', 'retention_policies', 'cleanup_runs', 'account_events', 'alembic_version']
    keys, digests = {}, {}
    for name in names:
        table = Table(name, MetaData(), autoload_with=connection)
        pk = list(table.primary_key.columns)
        query = select(table).order_by(*pk)
        if original is not None:
            query = query.where(tuple_(*pk).in_(original[name]))
        rows = [dict(row) for row in connection.execute(query).mappings()]
        keys[name] = [tuple(row[col.name] for col in pk) for row in rows]
        serialized = json.dumps(rows, sort_keys=True, default=str).encode()
        digests[name] = {'rows': len(rows), 'sha256': hashlib.sha256(serialized).hexdigest()}
    return keys, digests


def main():
    report = {'scope': 'Actual application against isolated hosted snapshot; no live restore or traffic switch',
              'snapshot_branch': 'br-orange-boat-b3dljf23', 'checks': [],
              'limitations': ['Historical plaintext session tokens were not available; original session records are fingerprinted and new synthetic sessions are exercised.',
                              'Expiring rate-limit buckets are operational data and excluded from business-row fingerprint checks.',
                              'No historical customer job is claimed or executed. Only the synthetic job is explicitly leased.']}
    path = Path('artifacts/hosted-recovery/results.json')
    path.parent.mkdir(parents=True, exist_ok=True)

    def record(feature):
        report['checks'].append({'feature': feature, 'status': 'PASS'})

    try:
        url = snapshot_url(os.environ.get('PREFLIGHT_RECOVERY_DATABASE_URL', ''))
        concurrency_guard()
        from fastapi.testclient import TestClient
        from sqlalchemy import text
        from app.main import create_app
        from app.db import User, Organization, Membership, Scan
        from app.security import hasher
        from app.worker import execute
        app = create_app(url, mode='development')
        with app.state.engine.connect() as connection:
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == '0006'
            original_keys, before = fingerprints(connection)
        record('Hosted snapshot schema 0006 and baseline captured')
        password, suffix = secrets.token_urlsafe(36), uuid.uuid4().hex
        concurrency_guard()
        with app.state.db() as db:
            owner = User(email='qa-restored-owner-' + suffix + '@example.test', password_hash=hasher.hash(password), verified=1)
            outsider = User(email='qa-restored-other-' + suffix + '@example.test', password_hash=hasher.hash(password), verified=1)
            first, second = Organization(name='Isolated restore acceptance A'), Organization(name='Isolated restore acceptance B')
            db.add_all([owner, outsider, first, second]); db.flush()
            db.add_all([Membership(org_id=first.id, user_id=owner.id, role='owner'), Membership(org_id=second.id, user_id=outsider.id, role='owner')]); db.commit()
            owner_email, outsider_email, org_id = owner.email, outsider.email, first.id
        with TestClient(app, raise_server_exceptions=False) as client:
            concurrency_guard()
            response = client.post('/api/auth/login', json={'email': owner_email, 'password': password})
            assert response.status_code == 200
            headers = {'X-CSRF-Token': response.json()['csrf_token']}
            assert client.get('/api/auth/me').status_code == 200
            record('Application login and new session on restored database')
            root = '/api/orgs/' + org_id
            baseline = {'openapi': '3.0.3', 'paths': {'/restore-proof': {'get': {'responses': {'200': {'description': 'OK'}}}}}}
            concurrency_guard()
            response = client.post(root + '/contracts', headers=headers, json={'baseline': baseline, 'proposed': {'openapi': '3.0.3', 'paths': {}}})
            assert response.status_code == 202
            scan_id, lease = response.json()['id'], str(uuid.uuid4())
            concurrency_guard()
            with app.state.db() as db:
                scan = db.get(Scan, scan_id)
                assert scan.org_id == org_id and scan.status == 'queued'
                scan.status, scan.lease, scan.attempts, scan.updated_at = 'running', lease, 1, time.time()
                db.commit()
            concurrency_guard()
            execute(app.state.db, scan_id, lease)
            response = client.get(root + '/scans/' + scan_id + '/report')
            assert response.status_code == 200
            report_data = response.json()
            assert report_data['status'] == 'completed'
            assert any(f['rule'] == 'OAS.ENDPOINT_REMOVED' for f in report_data['result']['findings'])
            record('Restored application and static worker produce known evidence')
            assert client.get(root + '/scans/' + scan_id + '/report?format=csv').status_code == 200
            record('Restored report JSON and CSV access')
            concurrency_guard()
            assert client.post('/api/auth/logout', headers=headers).status_code == 200
            concurrency_guard()
            assert client.post('/api/auth/login', json={'email': outsider_email, 'password': password}).status_code == 200
            assert client.get(root + '/scans/' + scan_id + '/report').status_code == 404
            record('Restored application tenant boundary rejects outsider')
        with app.state.engine.connect() as connection:
            _, after = fingerprints(connection, original_keys)
        assert before == after, 'Original snapshot business records changed'
        record('All original business rows and historical session records preserved')
        report['original_rows'] = {name: value['rows'] for name, value in before.items()}
        app.state.engine.dispose(); app.state.health_engine.dispose()
    except Exception as error:
        report['checks'].append({'feature': 'Hosted recovery acceptance', 'status': 'BLOCKED OR FAILED', 'error_type': type(error).__name__})
        raise SystemExit('Hosted recovery not verified; check secure prerequisite configuration and sanitized artifact') from None
    finally:
        path.write_text(json.dumps(report, indent=2))
        print(json.dumps({'passed': sum(x['status'] == 'PASS' for x in report['checks']),
                          'blocked_or_failed': sum(x['status'] != 'PASS' for x in report['checks'])}))


if __name__ == '__main__':
    main()
