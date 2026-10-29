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

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import select, delete, func, text
from sqlalchemy.exc import IntegrityError
from .db import Base, make_engine, factory, User, Organization, Membership, SessionRecord, Repository, Scan, Audit, FindingReview, FindingReviewEvent
from . import retention, alerts, email_recovery, operations, private_github, onboarding
from .db import RetentionPolicy, CleanupRun, RepositoryCredential, AccountEvent
from .job_signal import notify_worker
from .security import hasher, DUMMY_HASH, password_ok, digest, limit, principal, member, has_active_session, constant_equal
from .github import NAME, valid_ref, archive_url, download
from .analyzer import read_zip, MAX_BYTES
from .contracts import VERSION
from .observability import RequestDiagnostics, instrument_engine
from .comparisons import compare_results
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


class EmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class EmailConfirm(BaseModel):
    token: str = Field(min_length=1, max_length=128)


class EmailVerification(EmailConfirm):
    new_password: str | None = Field(default=None,min_length=14,max_length=256)


class Registration(BaseModel):
    email: str = Field(min_length=3,max_length=254)
    accepted_terms: bool = Field(strict=True)
    legal_version: str = Field(max_length=32)


class EmailReset(EmailConfirm):
    new_password: str = Field(min_length=14, max_length=256)


class RoleInput(BaseModel):
    role: str = Field(max_length=20)


class ReviewInput(BaseModel):
    status: str = Field(max_length=24)
    reason: str = Field(min_length=10, max_length=2000)
    expires_at: float | None = Field(default=None, allow_inf_nan=False)
    expected_version: int = Field(ge=0)


class RetentionInput(BaseModel):
    days: int | None = Field(default=None,ge=7,le=3650)
    expected_version: int = Field(ge=0)


class CleanupInput(BaseModel):
    confirmation: str = Field(max_length=100)
    reason: str = Field(min_length=10,max_length=1000)


class OrgInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class RepoInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=210)


class PrivateRepoInput(BaseModel):
    full_name: str = Field(min_length=3, max_length=210)
    token: SecretStr = Field(min_length=30, max_length=256)


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


def admit(db, org_id, actor_id=None):
    # Serialize admission per tenant on PostgreSQL to avoid quota/concurrency races.
    db.scalar(select(Organization).where(Organization.id == org_id).with_for_update())
    active = db.scalar(select(func.count()).select_from(Scan).where(Scan.org_id == org_id, Scan.status.in_(['queued', 'running'])))
    usage = db.scalar(select(func.count()).select_from(Scan).where(Scan.org_id == org_id, Scan.created_at > time.time() - 86400))
    if actor_id:
        db.scalar(select(User).where(User.id==actor_id).with_for_update())
        account_usage=db.scalar(select(func.count()).select_from(Scan).where(Scan.created_by==actor_id,Scan.created_at>time.time()-86400))
        if account_usage>=20:raise HTTPException(429,'Account quota: 20 scans per rolling day across organizations')
    if active >= 3 or usage >= 20:
        raise HTTPException(429, 'Staging quota: 3 pending scans and 20 scans per rolling day')


def create_app(database_url=None, mode=None):
    mode = mode or os.getenv('PREFLIGHT_MODE', 'development')
    if mode not in ('development','staging','production'):
        raise ValueError('Unsupported application mode')
    db_url = database_url or os.getenv('DATABASE_URL', 'sqlite:///./preflight.db')
    @asynccontextmanager
    async def lifespan(app):
        if mode in ('staging','production'):
            if not db_url.startswith(('postgres://', 'postgresql')):
                raise RuntimeError('Staging requires a PostgreSQL DATABASE_URL')
            if len(os.getenv('STAGING_PASSWORD', '')) < 24:
                raise RuntimeError('Staging requires a strong STAGING_PASSWORD')
        # Schema is managed by Alembic, never implicitly migrated by a web process.
        yield
        app.state.engine.dispose()
        app.state.health_engine.dispose()

    app = FastAPI(title='ZEVQ Preflight', version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.engine = make_engine(db_url)
    app.state.health_engine = make_engine(db_url, health=True)
    instrument_engine(app.state.engine)
    app.state.db = factory(app.state.engine)
    app.state.mode = mode

    @app.exception_handler(Exception)
    async def unexpected_error(request, error):
        reference=request.scope.get('preflight_request_id','unavailable')
        headers={'X-Request-ID':reference,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'self'; frame-ancestors 'none'"}
        if mode in ('staging','production'):headers['Strict-Transport-Security']='max-age=31536000'
        return JSONResponse({'detail':'Service temporarily unavailable. Retry or contact support with reference '+reference},status_code=500,headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo submitted credentials/source or non-finite input values.
        return JSONResponse({'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in error.errors()]},status_code=422)

    @app.middleware('http')
    async def boundaries(request, call_next):
        path = request.url.path
        public_access = path in ('/health', '/login', '/register', '/api/auth/login', '/api/auth/register', '/forgot-password', '/reset-password', '/verify-email', '/api/auth/email/status', '/api/auth/email/request-reset', '/api/auth/email/request-verification', '/api/auth/email/reset', '/api/auth/email/verify', '/api/operations/monitor') or path.startswith('/static/')
        public_marketing=path in ('/','/features','/how-it-works','/use-cases','/docs','/faq','/security','/pricing','/contact','/privacy','/terms') and os.getenv('PREFLIGHT_PUBLIC_ACCESS_ENABLED')=='1'
        if mode in ('staging','production') and not public_access and not public_marketing:
            expected = 'staging:' + os.getenv('STAGING_PASSWORD', '')
            supplied = request.headers.get('authorization', '')
            try:
                decoded = base64.b64decode(supplied.split(' ', 1)[1], validate=True).decode() if supplied.startswith('Basic ') else ''
            except (ValueError, UnicodeError):
                decoded = ''
            if not constant_equal(decoded, expected):
                try:
                    authenticated = has_active_session(request)
                except Exception:
                    return JSONResponse({'detail': 'Sign-in service is temporarily unavailable. Please retry.'}, status_code=503, headers={'Cache-Control':'no-store'})
                if not authenticated:
                    if request.method in ('GET', 'HEAD') and not path.startswith('/api/'):
                        return RedirectResponse('/login', status_code=303, headers={'Cache-Control':'no-store'})
                    return JSONResponse({'detail': 'Sign in required'}, status_code=401, headers={'Cache-Control':'no-store'})
        body_limit=16384 if path.startswith('/api/auth/') else MAX_BYTES*2+100_000
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            expected_origin = os.getenv('PUBLIC_ORIGIN', str(request.base_url).rstrip('/'))
            if origin and origin.rstrip('/') != expected_origin:
                return JSONResponse({'detail': 'Cross-origin mutation rejected'}, status_code=403)
            try:
                if int(request.headers.get('content-length', '0')) > body_limit:
                    return JSONResponse({'detail': 'Request too large'}, status_code=413)
            except ValueError:
                return JSONResponse({'detail': 'Invalid Content-Length'}, status_code=400)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            chunks, total = [], 0
            async for chunk in request.stream():
                total += len(chunk)
                if total > body_limit:
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
        if mode in ('staging','production'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    app.add_middleware(RequestDiagnostics)

    @app.get('/health')
    def health():
        try:
            with app.state.health_engine.connect() as conn:
                if conn.dialect.name == 'postgresql':
                    conn.execute(text("SET LOCAL statement_timeout = '1500ms'"))
                conn.execute(text('SELECT 1'))
        except Exception:
            return JSONResponse({'status': 'unavailable'}, status_code=503)
        return {'status': 'ok', 'version': VERSION, 'database': 'reachable'}

    @app.get('/api/operations/monitor')
    def monitor(request: Request):
        return operations.monitor_status(request)

    @app.get('/api/ready')
    def ready(request: Request):
        principal(request)
        with app.state.engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {'database': 'reachable', 'execution': 'disabled', 'registration': 'enabled' if onboarding.available() else 'disabled', 'billing': 'disabled'}

    @app.get('/api/auth/email/status')
    def email_status():
        return {'delivery_enabled': email_recovery.configuration() is not None, 'registration': 'enabled' if onboarding.available() else 'disabled','legal_version':onboarding.LEGAL_VERSION}

    def request_email(data, request, background, purpose):
        config = email_recovery.configuration()
        if config is None:
            raise HTTPException(503, 'Email delivery is not configured. Contact support for verified operator recovery.')
        email = data.email.strip().lower()
        limit(app.state.db, 'email-ip:' + (request.client.host if request.client else 'unknown'), 10, 900)
        limit(app.state.db, 'email-recipient:' + email, 3, 900)
        background.add_task(email_recovery.dispatch, app.state.db, config, email, purpose)
        return JSONResponse(email_recovery.GENERIC, status_code=202)

    @app.post('/api/auth/email/request-reset')
    def request_reset(data: EmailRequest, request: Request, background: BackgroundTasks):
        return request_email(data, request, background, 'reset')

    @app.post('/api/auth/email/request-verification')
    def request_verification(data: EmailRequest, request: Request, background: BackgroundTasks):
        return request_email(data, request, background, 'verify')

    def confirm_email(data, request, purpose):
        if email_recovery.configuration() is None:
            raise HTTPException(503, 'Email delivery is not configured. Contact support.')
        limit(app.state.db, 'email-confirm-ip:' + (request.client.host if request.client else 'unknown'), 20, 900)
        email_recovery.consume(app.state.db, data.token, purpose, getattr(data, 'new_password', None))
        response = JSONResponse({'ok': True, 'sign_in_required': True})
        response.delete_cookie('preflight_session', path='/')
        return response

    @app.post('/api/auth/email/reset')
    def reset_email(data: EmailReset, request: Request):
        return confirm_email(data, request, 'reset')

    @app.post('/api/auth/email/verify')
    def verify_email(data: EmailVerification, request: Request):
        return confirm_email(data, request, 'verify')

    @app.post('/api/auth/register')
    async def register(request: Request, background: BackgroundTasks):
        if not onboarding.available():
            raise HTTPException(403, 'Public registration is disabled pending verified email delivery and release approval. Contact zevqlabs@gmail.com.')
        if mode in ('staging','production') and os.getenv('PREFLIGHT_PUBLIC_ACCESS_ENABLED')!='1':
            # Allows a protected operator acceptance test before public launch.
            supplied=request.headers.get('authorization','')
            try:decoded=base64.b64decode(supplied.split(' ',1)[1],validate=True).decode() if supplied.startswith('Basic ') else ''
            except (ValueError,UnicodeError):decoded=''
            if not constant_equal(decoded,'staging:'+os.getenv('STAGING_PASSWORD','')):raise HTTPException(403,'Protected onboarding test requires operator authorization')
        limit(app.state.db,'register-ip:'+(request.client.host if request.client else 'unknown'),5,3600)
        try:
            data=Registration.model_validate(await request.json())
            email=onboarding.normalize_email(data.email)
        except Exception:raise HTTPException(422,'Enter a valid email address and accept the current terms and privacy notice.') from None
        if data.accepted_terms is not True or data.legal_version!=onboarding.LEGAL_VERSION:raise HTTPException(422,'Accept the current terms and privacy notice to register.')
        limit(app.state.db,'email-recipient:'+email,3,900)
        await run_in_threadpool(onboarding.provision,app.state.db,email)
        background.add_task(email_recovery.dispatch,app.state.db,email_recovery.configuration(),email,'verify')
        return JSONResponse(onboarding.GENERIC,status_code=202)

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
        response.set_cookie('preflight_session', token, httponly=True, secure=mode in ('staging','production'), samesite='strict', max_age=7 * 86400, path='/')
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
            from .db import EmailToken
            db.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
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

    @app.get('/api/orgs/{org_id}/alerts')
    def operational_alerts(org_id: str, request: Request):
        actor,_=member(request,org_id)
        with app.state.db() as db:return alerts.current_alerts(db,org_id,actor.id)

    @app.post('/api/orgs/{org_id}/alerts/{alert_id}/acknowledge')
    def acknowledge_alert(org_id: str, alert_id: str, request: Request):
        actor,_=member(request,org_id);limit(app.state.db,'alert-ack:'+actor.id,60,900)
        with app.state.db() as db:
            current=alerts.current_alerts(db,org_id,actor.id)
            found=next((a for a in current['alerts'] if a['id']==alert_id),None)
            if not found:raise HTTPException(404,'Alert not found in this organization')
            if not found['acknowledged']:event(db,org_id,actor.id,'alert.ack:'+alert_id);db.commit()
        return {'acknowledged':True}

    @app.get('/api/orgs/{org_id}/retention')
    def retention_policy(org_id: str, request: Request):
        member(request,org_id)
        with app.state.db() as db:return retention.policy_dict(db.get(RetentionPolicy,org_id))

    @app.put('/api/orgs/{org_id}/retention')
    def retention_update(org_id: str, data: RetentionInput, request: Request):
        actor,_=member(request,org_id,{'owner'})
        with app.state.db() as db:return retention.set_policy(db,org_id,actor.id,data.days,data.expected_version)

    @app.post('/api/orgs/{org_id}/retention/preview')
    def retention_preview(org_id: str, request: Request):
        actor,_=member(request,org_id,{'owner'});limit(app.state.db,'retention:'+org_id,10,900)
        with app.state.db() as db:return retention.preview(db,org_id,actor.id)

    @app.post('/api/orgs/{org_id}/retention/{run_id}/apply')
    def retention_apply(org_id: str, run_id: str, data: CleanupInput, request: Request):
        actor,_=member(request,org_id,{'owner'})
        if data.confirmation!='DELETE UNREVIEWED SCANS' or len(data.reason.strip())<10:raise HTTPException(422,'Enter the exact confirmation and a non-blank reason')
        with app.state.db() as db:return retention.apply(db,org_id,actor.id,run_id,data.reason.strip())

    @app.get('/api/orgs/{org_id}/retention/runs')
    def retention_runs(org_id: str, request: Request):
        member(request,org_id,{'owner'})
        with app.state.db() as db:return [retention.run_dict(r) for r in db.scalars(select(CleanupRun).where(CleanupRun.org_id==org_id).order_by(CleanupRun.created_at.desc()).limit(50))]

    @app.get('/api/orgs/{org_id}/repos')
    def repos(org_id: str, request: Request):
        member(request, org_id)
        with app.state.db() as db:
            return [{'id': r.id, 'full_name': r.full_name, 'source_kind': r.source_kind, 'credential_connected': bool(db.get(RepositoryCredential,r.id)) if r.source_kind=='private' else False} for r in db.scalars(select(Repository).where(Repository.org_id == org_id).limit(100))]

    @app.get('/api/orgs/{org_id}/private-github/status')
    def private_status(org_id: str, request: Request):
        member(request,org_id)
        return {'enabled': private_github.cipher() is not None, 'model':'repository-specific fine-grained token; GitHub App/OAuth unavailable'}

    @app.post('/api/orgs/{org_id}/private-github/repos', status_code=201)
    async def connect_private(org_id: str, data: PrivateRepoInput, request: Request):
        actor,_=member(request,org_id,{'owner'})
        limit(app.state.db,'private-connect:'+actor.id,5,900)
        name=data.full_name.strip();token=data.token.get_secret_value()
        if not NAME.fullmatch(name):raise HTTPException(422,'Repository must be owner/name')
        if len(token)>256:raise HTTPException(422,'Invalid credential length')
        try:
            private_github.require_enabled()
            # Validate credential format before any network call.
            private_github.validate_token(token)
            await private_github.verify(token,name)
        except ValueError as error:raise HTTPException(422,str(error)) from None
        with app.state.db() as db:
            db.scalar(select(Organization).where(Organization.id==org_id).with_for_update())
            repo=db.scalar(select(Repository).where(Repository.org_id==org_id,Repository.full_name==name))
            if repo and repo.source_kind!='private':raise HTTPException(409,'Disconnect the public entry before adding private access.')
            if not repo:
                if db.scalar(select(func.count()).select_from(Repository).where(Repository.org_id==org_id))>=20:raise HTTPException(429,'Staging repository limit reached')
                repo=Repository(org_id=org_id,full_name=name,source_kind='private');db.add(repo);db.flush()
            row=db.get(RepositoryCredential,repo.id)
            version=row.version+1 if row else 1
            encrypted=private_github.seal(repo,token,version)
            private_github.cancel_jobs(db,org_id,repo.id)
            if row:row.ciphertext=encrypted;row.version=version
            else:db.add(RepositoryCredential(repo_id=repo.id,org_id=org_id,ciphertext=encrypted,version=version))
            event(db,org_id,actor.id,'github.private_connected');db.commit()
            return {'id':repo.id,'full_name':repo.full_name,'source_kind':'private','credential_connected':True}

    @app.get('/api/orgs/{org_id}/repos/{repo_id}/revisions/{kind}')
    async def private_revisions(org_id: str,repo_id: str,kind: str,request: Request,ref: str='',page: int=1):
        actor,_=member(request,org_id);limit(app.state.db,'private-revisions:'+actor.id,30,900)
        with app.state.db() as db:
            repo=db.get(Repository,repo_id)
            if not repo or repo.org_id!=org_id:raise HTTPException(404,'Repository not found')
            try:repo,token,_=private_github.credential(db,org_id,repo_id)
            except ValueError as error:raise HTTPException(409,str(error)) from None
        try:return await private_github.revisions(token,repo.full_name,kind,ref,page)
        except ValueError as error:raise HTTPException(422,str(error)) from None

    @app.delete('/api/orgs/{org_id}/repos/{repo_id}/credential')
    def disconnect_private(org_id: str,repo_id: str,request: Request):
        actor,_=member(request,org_id,{'owner'})
        with app.state.db() as db:
            db.scalar(select(Organization).where(Organization.id==org_id).with_for_update())
            repo=db.get(Repository,repo_id)
            if not repo or repo.org_id!=org_id or repo.source_kind!='private':raise HTTPException(404,'Private repository not found')
            private_github.cancel_jobs(db,org_id,repo_id)
            db.execute(delete(RepositoryCredential).where(RepositoryCredential.repo_id==repo_id,RepositoryCredential.org_id==org_id))
            event(db,org_id,actor.id,'github.private_disconnected');db.commit()
        return {'ok':True,'provider_revocation_required':True}

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
            db.scalar(select(Organization).where(Organization.id==org_id).with_for_update())
            private_github.cancel_jobs(db,org_id,repo_id)
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
            admit(db, org_id, user.id)
            payload=None
            if repo.source_kind=='private':
                try:_,_,version=private_github.credential(db,org_id,repo.id)
                except ValueError as error:raise HTTPException(409,str(error)) from None
                payload=json.dumps({'private_repository_id':repo.id,'credential_version':version})
            scan = Scan(org_id=org_id, created_by=user.id, repository=repo.full_name, base_ref=data.base_ref, head_ref=data.head_ref, idempotency_key=key,payload=payload)
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
            admit(db, org_id, user.id)
            scan = Scan(org_id=org_id, created_by=user.id, payload=json.dumps(payload)); db.add(scan)
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
            admit(db, org_id, user.id)
            scan = Scan(org_id=org_id, created_by=user.id, repository='OpenAPI contract', payload=payload); db.add(scan)
            event(db, org_id, user.id, 'contract.queued'); db.commit()
            notify_worker()
            return scan_dict(scan, True)

    @app.get('/api/orgs/{org_id}/comparisons')
    def compare_scans(org_id: str, request: Request, baseline_id: str, proposed_id: str):
        member(request,org_id)
        with app.state.db() as db:
            baseline=scoped_scan(db,org_id,baseline_id)
            proposed=scoped_scan(db,org_id,proposed_id)
            if baseline.id==proposed.id:raise HTTPException(422,'Choose two different scans')
            if baseline.status!='completed' or proposed.status!='completed':
                raise HTTPException(409,'Both scans must be completed')
            if baseline.repository!=proposed.repository:
                raise HTTPException(422,'Choose scans with the same source label')
            old,new=json.loads(baseline.result or '{}'),json.loads(proposed.result or '{}')
            data=compare_results(old,new)
            for name,scan,result in [('baseline',baseline,old),('proposed',proposed,new)]:
                data[name]={**scan_dict(scan),'engine_version':result.get('engine_version'),'risk_score':result.get('risk_score'),'coverage':result.get('coverage')}
            if baseline.repository in ('Uploaded archive','OpenAPI contract'):
                data['warnings'].append('Uploaded inputs have no verified shared source identity. Confirm these reports describe the same project and intended comparison.')
            if (baseline.base_ref,baseline.head_ref)!=(proposed.base_ref,proposed.head_ref):
                data['warnings'].append('Requested revision pairs differ. This compares stored findings, not the code between these scans.')
            data['warnings'].append('Chronological order and equivalent test coverage are not guaranteed. Inspect source revisions and timestamps.')
            return data

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
            events=[{'action':e.action,'created_at':e.created_at} for e in db.scalars(select(AccountEvent).where(AccountEvent.user_id==user.id).order_by(AccountEvent.created_at.desc()).limit(1000))]
        return {'id': user.id, 'email': user.email, 'memberships': memberships,'account_events':events,'account_events_limit':1000}

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
        if path not in ('', 'login', 'register', 'forgot-password', 'reset-password', 'verify-email', 'app', 'docs', 'security', 'pricing', 'contact', 'privacy', 'terms', 'features', 'how-it-works', 'use-cases', 'faq'):
            if path.startswith('api/'):
                return JSONResponse({'detail': 'Endpoint not found'}, status_code=404)
            return FileResponse(ROOT / 'static/index.html', status_code=404)
        return FileResponse(ROOT / 'static/index.html')
    return app


app = create_app()
