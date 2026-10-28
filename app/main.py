"""ZEVQ Preflight protected static-analysis workspace."""
import base64
import csv
import io
import json
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, delete, func, text
from sqlalchemy.exc import IntegrityError
from .db import Base, make_engine, factory, User, Organization, Membership, SessionRecord, Repository, Scan, Audit, FindingReview, FindingReviewEvent
from .job_signal import notify_worker
from .security import hasher, DUMMY_HASH, password_ok, digest, limit, principal, member, has_active_session
from .github import NAME, valid_ref, archive_url, download
from .analyzer import read_zip, MAX_BYTES
from .contracts import VERSION
from .reviews import STATUSES, MAX_SUPPRESSION_SECONDS, decision_dict, annotate_scan

ROOT = Path(__file__).resolve().parent.parent
WRITERS = {'owner', 'administrator', 'developer'}
ADMINS = {'owner', 'administrator'}


class Login(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=14, max_length=256)


class RoleInput(BaseModel):
    role: str = Field(max_length=20)


class ReviewInput(BaseModel):
    status: str = Field(max_length=24)
    reason: str = Field(min_length=10, max_length=2000)
    expires_at: float | None = Field(default=None, allow_inf_nan=False)
    expected_version: int = Field(ge=0)


class OrgInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class RepoInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=210)


class ScanInput(BaseModel):
    repository_id: str
    base_ref: str = Field(default='', max_length=120)
    head_ref: str = Field(default='main', max_length=120)


class ContractInput(BaseModel):
    baseline: dict
    proposed: dict


class MemberInput(BaseModel):
    email: str = Field(max_length=254)
    role: str


def event(db, org_id, user_id, action):
    db.add(Audit(org_id=org_id, actor_id=user_id, action=action))


def scan_dict(scan, details=False):
    data = {key: getattr(scan, key) for key in ('id', 'status', 'created_at', 'repository', 'base_ref', 'head_ref', 'error', 'attempts')}
    result = json.loads(scan.result) if scan.result else None
    if details:
        data['result'] = result
    else:
        data['risk_level'] = result.get('risk_level') if result else None
        data['finding_count'] = len(result.get('findings', [])) if result else 0
    return data


def scoped_scan(db, org_id, scan_id):
    scan = db.scalar(select(Scan).where(Scan.id == scan_id, Scan.org_id == org_id))
    if not scan:
        raise HTTPException(404, 'Scan not found')
    return scan


def admit(db, org_id):
    # Serialize admission per tenant on PostgreSQL to avoid quota/concurrency races.
    db.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
    active = db.scalar(select(func.count()).select_from(Scan).where(Scan.org_id == org_id, Scan.status.in_(['queued', 'running'])))
    usage = db.scalar(select(func.count()).select_from(Scan).where(Scan.org_id == org_id, Scan.created_at > time.time() - 86400))
    if active >= 3 or usage >= 20:
        raise HTTPException(429, 'Staging quota: 3 pending scans and 20 scans per rolling day')


def create_app(database_url=None, mode=None):
    mode = mode or os.getenv('PREFLIGHT_MODE', 'development')
    db_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///./preflight.db')
    @asynccontextmanager
    async def lifespan(app):
        if mode == 'staging':
            if not db_url.startswith(('postgres://', 'postgresql')):
                raise RuntimeError('Staging requires a PostgreSQL DATABASE_URL')
            if len(os.getenv('STAGING_PASSWORD', '')) < 24:
                raise RuntimeError('Staging requires a strong STAGING_PASSWORD')
        # Schema is managed by Alembic, never implicitly migrated by a web process.
        yield
        app.state.engine.dispose()

    app = FastAPI(title='ZEVQ Preflight', version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.engine = make_engine(db_url)
    app.state.db = factory(app.state.engine)
    app.state.mode = mode

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo submitted credentials/source or non-finite input values.
        return JSONResponse({'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in error.errors()]},status_code=422)

    @app.middleware('http')
    async def boundaries(request, call_next):
        path = request.url.path
        public_access = path in ('/health', '/login', '/api/auth/login', '/api/auth/register') or path.startswith('/static/')
        if mode == 'staging' and not public_access:
            expected = 'staging:' + os.getenv('STAGING_PASSWORD', '')
            supplied = request.headers.get('authorization', '')
            try:
                decoded = base64.b64decode(supplied.split(' ', 1)[1], validate=True).decode() if supplied.startswith('Basic ') else ''
            except (ValueError, UnicodeError):
                decoded = ''
            if not secrets.compare_digest(decoded, expected):
                try:
                    authenticated = has_active_session(request)
                except Exception:
                    return JSONResponse({'detail': 'Sign-in service is temporarily unavailable. Please retry.'}, status_code=503, headers={'Cache-Control':'no-store'})
                if not authenticated:
                    if request.method in ('GET', 'HEAD') and not path.startswith('/api/'):
                        return RedirectResponse('/login', status_code=303, headers={'Cache-Control':'no-store'})
                    return JSONResponse({'detail': 'Sign in required'}, status_code=401, headers={'Cache-Control':'no-store'})
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            expected_origin = os.getenv('PUBLIC_ORIGIN', str(request.base_url).rstrip('/'))
            if origin and origin.rstrip('/') != expected_origin:
                return JSONResponse({'detail': 'Cross-origin mutation rejected'}, status_code=403)
            try:
                if int(request.headers.get('content-length', '0')) > MAX_BYTES * 2 + 100_000:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': 'Invalid Content-Length'}, status_code=400)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            chunks, total = [], 0
            async for chunk in request.stream():
                total += len(chunk)
                if total > MAX_BYTES * 2 + 100_000:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        return response

    @app.middleware('http')
    async def secure_response_headers(request, call_next):
        # Registered last so even early authentication/validation responses pass here.
        response = await call_next(request)
        response.headers.update({'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'", 'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'})
        if mode == 'staging':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.get('/health')
    def health():
        return {'status': 'ok', 'version': VERSION}

    @app.get('/api/ready')
    def ready(request: Request):
        principal(request)
        with app.state.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'database': 'reachable', 'execution': 'disabled', 'registration': 'disabled', 'billing': 'disabled'}

    @app.post('/api/auth/register')
    def register():
        raise HTTPException(403, 'Public registration is disabled pending launch approval. Contact zevqlabs@gmail.com.')

    @app.post('/api/auth/login')
    def login(data: Login, request: Request):
        email = data.email.strip().lower()
        limit(app.state.db, 'login-ip:' + (request.client.host if request.client else 'unknown'), 30, 900)
        limit(app.state.db, 'login-email:' + email, 10, 900)
        with app.state.db() as db:
            user = db.scalar(select(User).where(User.email == email))
            valid = password_ok(user.password_hash if user else DUMMY_HASH, data.password)
            if not user or not valid or not user.verified:
                raise HTTPException(401, 'Invalid credentials or account not verified')
            token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
            db.add(SessionRecord(token_hash=digest(token), user_id=user.id, csrf=csrf, expires=time.time() + 7 * 86400))
            db.commit()
        response = JSONResponse({'csrf_token': csrf})
        response.set_cookie('preflight_session', token, httponly=True, secure=mode == 'staging', samesite='strict', max_age=7 * 86400, path='/')
        return response

    @app.get('/api/auth/me')
    def me(request: Request):
        user, session = principal(request)
        with app.state.db() as db:
            rows = db.execute(select(Organization, Membership.role).join(Membership).where(Membership.user_id == user.id)).all()
        return {'id': user.id, 'email': user.email, 'csrf_token': session.csrf, 'organizations': [{'id': org.id, 'name': org.name, 'role': role} for org, role in rows]}

    @app.post('/api/auth/logout')
    def logout(request: Request):
        _, session = principal(request)
        with app.state.db() as db:
            db.execute(delete(SessionRecord).where(SessionRecord.token_hash == session.token_hash)); db.commit()
        response = JSONResponse({'ok': True}); response.delete_cookie('preflight_session', path='/')
        return response

    @app.post('/api/auth/password')
    def change_password(data: PasswordChange, request: Request):
        user, _ = principal(request)
        limit(app.state.db, 'password-change:' + user.id, 5, 900)
        with app.state.db() as db:
            current = db.scalar(select(User).where(User.id == user.id).with_for_update())
            if not current or not password_ok(current.password_hash, data.current_password):
                raise HTTPException(403, 'Current password is incorrect')
            if password_ok(current.password_hash, data.new_password):
                raise HTTPException(422, 'Choose a different new password')
            current.password_hash = hasher.hash(data.new_password)
            db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id))
            for org_id in db.scalars(select(Membership.org_id).where(Membership.user_id == user.id)):
                event(db, org_id, user.id, 'account.password_changed')
            db.commit()
        response = JSONResponse({'ok': True, 'sign_in_required': True})
        response.delete_cookie('preflight_session', path='/')
        return response

    @app.post('/api/auth/logout-all')
    def logout_all(request: Request):
        user, _ = principal(request)
        with app.state.db() as db:
            db.execute(delete(SessionRecord).where(SessionRecord.user_id == user.id)); db.commit()
        response = JSONResponse({'ok': True}); response.delete_cookie('preflight_session', path='/')
        return response

    @app.post('/api/orgs', status_code=201)
    def new_org(data: OrgInput, request: Request):
        user, _ = principal(request)
        limit(app.state.db, 'org-create:' + user.id, 5, 86400)
        with app.state.db() as db:
            org = Organization(name=data.name.strip()); db.add(org); db.flush()
            db.add(Membership(org_id=org.id, user_id=user.id, role='owner'))
            event(db, org.id, user.id, 'organization.created'); db.commit()
            return {'id': org.id, 'name': org.name}

    @app.get('/api/orgs/{org_id}/repos')
    def repos(org_id: str, request: Request):
        member(request, org_id)
        with app.state.db() as db:
            return [{'id': r.id, 'full_name': r.full_name} for r in db.scalars(select(Repository).where(Repository.org_id == org_id).limit(100))]

    @app.post('/api/orgs/{org_id}/repos', status_code=201)
    def add_repo(org_id: str, data: RepoInput, request: Request):
        user, _ = member(request, org_id, WRITERS)
        name = data.full_name.strip()
        if not NAME.fullmatch(name):
            raise HTTPException(422, 'Repository must be owner/name')
        with app.state.db() as db:
            org = db.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
            if db.scalar(select(func.count()).select_from(Repository).where(Repository.org_id == org_id)) >= 20:
                raise HTTPException(429, 'Staging repository limit reached')
            repo = Repository(org_id=org_id, full_name=name); db.add(repo)
            event(db, org_id, user.id, 'repository.connected')
            try: db.commit()
            except IntegrityError: raise HTTPException(409, 'Repository already connected')
            return {'id': repo.id, 'full_name': repo.full_name}

    @app.delete('/api/orgs/{org_id}/repos/{repo_id}')
    def remove_repo(org_id: str, repo_id: str, request: Request):
        user, _ = member(request, org_id, ADMINS)
        with app.state.db() as db:
            result = db.execute(delete(Repository).where(Repository.id == repo_id, Repository.org_id == org_id))
            if not result.rowcount: raise HTTPException(404, 'Repository not found')
            event(db, org_id, user.id, 'repository.disconnected'); db.commit()
        return {'ok': True}

    @app.get('/api/orgs/{org_id}/scans')
    def scans(org_id: str, request: Request, offset: int = 0):
        member(request, org_id)
        if offset < 0: raise HTTPException(422, 'Invalid offset')
        with app.state.db() as db:
            return [scan_dict(s) for s in db.scalars(select(Scan).where(Scan.org_id == org_id).order_by(Scan.created_at.desc()).offset(offset).limit(100))]

    @app.post('/api/orgs/{org_id}/scans', status_code=202)
    def queue_scan(org_id: str, data: ScanInput, request: Request):
        user, _ = member(request, org_id, WRITERS)
        try:
            valid_ref(data.head_ref)
            if data.base_ref: valid_ref(data.base_ref)
        except ValueError as exc: raise HTTPException(422, str(exc))
        key = request.headers.get('Idempotency-Key')
        if key and len(key) > 100: raise HTTPException(422, 'Invalid idempotency key')
        with app.state.db() as db:
            db.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
            repo = db.scalar(select(Repository).where(Repository.org_id == org_id, Repository.id == data.repository_id))
            if not repo: raise HTTPException(404, 'Repository not found')
            if key:
                existing = db.scalar(select(Scan).where(Scan.org_id == org_id, Scan.idempotency_key == key))
                if existing:
                    if (existing.repository, existing.base_ref, existing.head_ref) != (repo.full_name, data.base_ref, data.head_ref):
                        raise HTTPException(409, 'Idempotency key already used for different inputs')
                    return scan_dict(existing, True)
            admit(db, org_id)
            scan = Scan(org_id=org_id, repository=repo.full_name, base_ref=data.base_ref, head_ref=data.head_ref, idempotency_key=key)
            db.add(scan); event(db, org_id, user.id, 'scan.queued'); db.commit()
            notify_worker()
            return scan_dict(scan, True)

    @app.post('/api/orgs/{org_id}/scans/zip', status_code=202)
    async def upload(org_id: str, request: Request, file: UploadFile = File(...), baseline: UploadFile | None = File(None)):
        user, _ = member(request, org_id, WRITERS)
        try:
            files = read_zip(await file.read(MAX_BYTES + 1))
            old = read_zip(await baseline.read(MAX_BYTES + 1)) if baseline else None
        except ValueError as exc: raise HTTPException(422, str(exc))
        payload = {'files': files, 'baseline': old, 'skipped': getattr(files, 'skipped', []), 'baseline_skipped': getattr(old, 'skipped', [])}
        with app.state.db() as db:
            admit(db, org_id)
            scan = Scan(org_id=org_id, payload=json.dumps(payload)); db.add(scan)
            event(db, org_id, user.id, 'scan.uploaded'); db.commit()
            notify_worker()
            return scan_dict(scan, True)

    @app.post('/api/orgs/{org_id}/contracts', status_code=202)
    def contracts(org_id: str, data: ContractInput, request: Request):
        user, _ = member(request, org_id, WRITERS)
        payload = json.dumps({'contracts': data.model_dump()})
        if len(payload.encode()) > MAX_BYTES: raise HTTPException(413, 'Contract too large')
        for spec in (data.baseline, data.proposed):
            if not str(spec.get('openapi', '')).startswith('3.') or not isinstance(spec.get('paths'), dict):
                raise HTTPException(422, 'Provide OpenAPI 3.x documents with paths objects')
        with app.state.db() as db:
            admit(db, org_id)
            scan = Scan(org_id=org_id, repository='OpenAPI contract', payload=payload); db.add(scan)
            event(db, org_id, user.id, 'contract.queued'); db.commit()
            notify_worker()
            return scan_dict(scan, True)

    @app.get('/api/orgs/{org_id}/scans/{scan_id}')
    def detail(org_id: str, scan_id: str, request: Request):
        member(request, org_id)
        with app.state.db() as db:
            scan = scoped_scan(db, org_id, scan_id)
            if scan.status == 'queued': notify_worker()
            return annotate_scan(db,scan_dict(scan,True))

    @app.post('/api/orgs/{org_id}/scans/{scan_id}/cancel')
    def cancel(org_id: str, scan_id: str, request: Request):
        user, _ = member(request, org_id, WRITERS)
        with app.state.db() as db:
            scan = scoped_scan(db, org_id, scan_id)
            if scan.status not in ('queued', 'running'): raise HTTPException(409, 'Scan cannot be cancelled')
            scan.status = 'cancelled'; scan.payload = None; scan.updated_at = time.time()
            event(db, org_id, user.id, 'scan.cancelled'); db.commit()
        return {'status': 'cancelled'}

    @app.get('/api/orgs/{org_id}/scans/{scan_id}/report')
    def report(org_id: str, scan_id: str, request: Request, format: str = 'json'):
        member(request, org_id)
        with app.state.db() as db:
            scan = scoped_scan(db, org_id, scan_id)
            if scan.status != 'completed': raise HTTPException(409, 'Report is not ready')
            data = annotate_scan(db,scan_dict(scan,True))
        if format == 'json':
            return Response(json.dumps(data, indent=2), media_type='application/json', headers={'Content-Disposition': f'attachment; filename="preflight-{scan_id}.json"'})
        if format != 'csv': raise HTTPException(422, 'Supported formats: json, csv')
        output = io.StringIO(); writer = csv.writer(output)
        fields = ['id', 'severity', 'category', 'file', 'line', 'message', 'confidence', 'recommended_action', 'review_status', 'review_reason', 'review_expires_at', 'review_version']
        writer.writerow(fields)
        for finding in data['result'].get('findings', []):
            review=data['reviews'].get(finding.get('id'),{})
            finding={**finding,'review_status':review.get('effective_status','open'),'review_reason':review.get('reason',''),'review_expires_at':review.get('expires_at') or '', 'review_version':review.get('version',0)}
            row = []
            for field in fields:
                value = str(finding.get(field, ''))
                if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')): value = "'" + value
                row.append(value)
            writer.writerow(row)
        return Response(output.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="preflight-{scan_id}.csv"'})

    @app.put('/api/orgs/{org_id}/scans/{scan_id}/findings/{finding_id}/review')
    def review_finding(org_id: str, scan_id: str, finding_id: str, data: ReviewInput, request: Request):
        actor,_=member(request,org_id,WRITERS)
        if data.status not in STATUSES:
            raise HTTPException(422,'Unsupported review decision')
        if data.status=='suppressed':
            member(request,org_id,ADMINS)
            now=time.time()
            if data.expires_at is None or not now<data.expires_at<=now+MAX_SUPPRESSION_SECONDS:
                raise HTTPException(422,'Suppression expiry must be in the future and within 90 days')
        elif data.expires_at is not None:
            raise HTTPException(422,'Expiry applies only to suppression decisions')
        reason=data.reason.strip()
        if len(reason)<10:
            raise HTTPException(422,'Provide a review reason of at least 10 non-blank characters')
        limit(app.state.db,'finding-review:'+actor.id,120,900)
        with app.state.db() as db:
            # Serialize decisions for this scan, including first-review creation.
            scan=db.scalar(select(Scan).where(Scan.id==scan_id,Scan.org_id==org_id).with_for_update())
            if not scan: raise HTTPException(404,'Scan not found')
            if scan.status!='completed': raise HTTPException(409,'Only completed scans can be reviewed')
            if not any(f.get('id')==finding_id for f in json.loads(scan.result or '{}').get('findings',[])):
                raise HTTPException(404,'Finding not found in this scan')
            current=db.get(FindingReview,(scan_id,finding_id))
            if data.expected_version!=(current.version if current else 0):
                raise HTTPException(409,'This decision changed. Reload the report before updating it.')
            values=dict(version=data.expected_version+1,status=data.status,reason=reason,expires_at=data.expires_at,actor_id=actor.id,updated_at=time.time())
            if current:
                for key,value in values.items():setattr(current,key,value)
            else:
                current=FindingReview(scan_id=scan_id,finding_id=finding_id,**values);db.add(current)
            db.add(FindingReviewEvent(scan_id=scan_id,finding_id=finding_id,**values))
            event(db,org_id,actor.id,'finding.'+data.status+':'+finding_id[:64])
            db.commit()
            return decision_dict(current)

    @app.get('/api/orgs/{org_id}/scans/{scan_id}/findings/{finding_id}/reviews')
    def review_history(org_id: str, scan_id: str, finding_id: str, request: Request, offset: int=0):
        member(request,org_id)
        if offset<0:raise HTTPException(422,'Invalid offset')
        with app.state.db() as db:
            scan=scoped_scan(db,org_id,scan_id)
            if not any(f.get('id')==finding_id for f in json.loads(scan.result or '{}').get('findings',[])):
                raise HTTPException(404,'Finding not found in this scan')
            rows=db.scalars(select(FindingReviewEvent).where(FindingReviewEvent.scan_id==scan_id,FindingReviewEvent.finding_id==finding_id).order_by(FindingReviewEvent.version.desc()).offset(offset).limit(100)).all()
            return [decision_dict(row) for row in rows]

    @app.get('/api/orgs/{org_id}/dashboard')
    def dashboard(org_id: str, request: Request):
        member(request, org_id)
        with app.state.db() as db:
            rows = db.scalars(select(Scan).where(Scan.org_id == org_id).order_by(Scan.created_at.desc()).limit(500)).all()
            repository_count = db.scalar(select(func.count()).select_from(Repository).where(Repository.org_id == org_id))
        severity = dict.fromkeys(['critical', 'high', 'medium', 'low', 'info'], 0); statuses = {}
        for scan in rows:
            statuses[scan.status] = statuses.get(scan.status, 0) + 1
            for finding in json.loads(scan.result or '{}').get('findings', []):
                level = finding.get('severity')
                if level in severity: severity[level] += 1
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone.utc).date()
        trend = {str(today - timedelta(days=i)): 0 for i in reversed(range(7))}
        latest = []
        for scan in rows:
            findings = json.loads(scan.result or '{}').get('findings', [])
            day = str(datetime.fromtimestamp(scan.created_at, timezone.utc).date())
            if day in trend: trend[day] += len(findings)
            for finding in findings:
                if len(latest) < 5:
                    latest.append({**finding, 'scan_id': scan.id})
        return {'repositories': repository_count, 'scans': len(rows), 'findings': sum(severity.values()), 'by_severity': severity, 'scan_status': statuses, 'recent_scans': [scan_dict(s) for s in rows[:10]], 'window': 'latest 500 scans', 'latest_findings': latest, 'finding_trend': [{'date': day, 'count': count} for day, count in trend.items()]}

    @app.get('/api/orgs/{org_id}/audit')
    def audit(org_id: str, request: Request):
        member(request, org_id, ADMINS)
        with app.state.db() as db:
            return [{'action': a.action, 'created_at': a.created_at, 'actor_id': a.actor_id} for a in db.scalars(select(Audit).where(Audit.org_id == org_id).order_by(Audit.created_at.desc()).limit(100))]

    @app.get('/api/orgs/{org_id}/members')
    def members(org_id: str, request: Request):
        member(request, org_id)
        with app.state.db() as db:
            return [{'email': u.email, 'user_id': u.id, 'role': m.role} for u, m in db.execute(select(User, Membership).join(Membership).where(Membership.org_id == org_id))]

    @app.post('/api/orgs/{org_id}/members', status_code=201)
    def add_member(org_id: str, data: MemberInput, request: Request):
        actor, _ = member(request, org_id, {'owner'})
        if data.role not in {'administrator', 'developer', 'viewer'}: raise HTTPException(422, 'Invalid role')
        with app.state.db() as db:
            user = db.scalar(select(User).where(User.email == data.email.strip().lower(), User.verified == 1))
            if not user: raise HTTPException(404, 'Provisioned verified account required; email invitations are not configured')
            if db.get(Membership, (org_id, user.id)): raise HTTPException(409, 'Already a member')
            db.add(Membership(org_id=org_id, user_id=user.id, role=data.role))
            event(db, org_id, actor.id, 'member.added'); db.commit()
        return {'ok': True}

    @app.patch('/api/orgs/{org_id}/members/{user_id}')
    def update_role(org_id: str, user_id: str, data: RoleInput, request: Request):
        actor, _ = member(request, org_id, {'owner'})
        if data.role not in {'administrator', 'developer', 'viewer'}:
            raise HTTPException(422, 'Invalid role; ownership transfer is not supported')
        with app.state.db() as db:
            membership = db.scalar(select(Membership).where(Membership.org_id == org_id, Membership.user_id == user_id).with_for_update())
            if not membership:
                raise HTTPException(404, 'Member not found')
            if membership.role == 'owner':
                raise HTTPException(409, 'Owner role cannot be changed here')
            membership.role = data.role
            event(db, org_id, actor.id, 'member.role_' + data.role + ':' + user_id)
            db.commit()
        return {'ok': True, 'role': data.role}

    @app.delete('/api/orgs/{org_id}/members/{user_id}')
    def remove_member(org_id: str, user_id: str, request: Request):
        actor, _ = member(request, org_id, {'owner'})
        with app.state.db() as db:
            m = db.get(Membership, (org_id, user_id))
            if not m: raise HTTPException(404, 'Member not found')
            if m.role == 'owner': raise HTTPException(409, 'Owner removal requires ownership transfer')
            db.delete(m); event(db, org_id, actor.id, 'member.removed'); db.commit()
        return {'ok': True}

    @app.get('/api/auth/export')
    def export_account(request: Request):
        user, _ = principal(request)
        with app.state.db() as db:
            memberships = [{'org_id': m.org_id, 'role': m.role} for m in db.scalars(select(Membership).where(Membership.user_id == user.id))]
        return {'id': user.id, 'email': user.email, 'memberships': memberships}

    @app.delete('/api/auth/account')
    def delete_account(request: Request):
        user, _ = principal(request)
        with app.state.db() as db:
            if db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.role == 'owner')):
                raise HTTPException(409, 'Delete owned organizations before deleting your account')
            db.execute(delete(User).where(User.id == user.id)); db.commit()
        response = JSONResponse({'ok': True}); response.delete_cookie('preflight_session', path='/'); return response

    @app.delete('/api/orgs/{org_id}')
    def delete_org(org_id: str, request: Request):
        member(request, org_id, {'owner'})
        with app.state.db() as db:
            db.execute(delete(Organization).where(Organization.id == org_id)); db.commit()
        return {'ok': True}

    # Original unauthenticated scan routes are deliberately retired.
    @app.post('/api/scan/{source}')
    def legacy(source: str, request: Request):
        principal(request)
        raise HTTPException(410, 'Use the organization-scoped scan API')

    app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
    @app.get('/{path:path}', include_in_schema=False)
    def page(path: str):
        if path not in ('', 'login', 'app', 'docs', 'security', 'pricing', 'contact', 'privacy', 'terms', 'features', 'how-it-works', 'use-cases', 'faq'):
            if path.startswith('api/'):
                return JSONResponse({'detail': 'Endpoint not found'}, status_code=404)
            return FileResponse(ROOT / 'static/index.html', status_code=404)
        return FileResponse(ROOT / 'static/index.html')
    return app


app = create_app()
