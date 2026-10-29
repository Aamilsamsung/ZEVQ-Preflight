"""Opt-in, per-repository fine-grained credentials. Never uses connector credentials.

Only fixed GitHub APIs are called. Server encryption keys stay outside the DB.
Encrypted claims bind the credential to its organization, repository and version.
"""
import json
import os
import re
import time
from urllib.parse import quote
import httpx
from cryptography.fernet import Fernet, InvalidToken
from .db import Repository, RepositoryCredential
from .github import NAME, valid_ref, download


def cipher():
    if os.getenv('PREFLIGHT_PRIVATE_GITHUB_ENABLED') != '1':
        return None
    try:return Fernet(os.environ['PREFLIGHT_CREDENTIAL_KEY'].encode())
    except (KeyError,ValueError):return None


def require_enabled():
    if cipher() is None:raise ValueError('Private GitHub access is disabled; an operator must configure the encryption key and enable it.')


def validate_token(token):
    if not re.fullmatch(r'github_pat_[A-Za-z0-9_]{20,240}',token):
        raise ValueError('Use a fine-grained GitHub token restricted to the selected repository with Contents read-only permission. Classic tokens are not accepted.')


def seal(repo, token, version):
    require_enabled()
    validate_token(token)
    return cipher().encrypt(json.dumps({'org':repo.org_id,'repo':repo.id,'name':repo.full_name,'version':version,'token':token}).encode()).decode()


def credential(db, org_id, repo_id, version=None):
    require_enabled()
    repo=db.get(Repository,repo_id);row=db.get(RepositoryCredential,repo_id)
    if not repo or repo.org_id!=org_id or repo.source_kind!='private' or not row or row.org_id!=org_id:
        raise ValueError('Private repository credential is disconnected or unavailable.')
    if version is not None and row.version!=version:raise ValueError('Private repository credential changed; start a new scan.')
    try:
        data=json.loads(cipher().decrypt(row.ciphertext.encode()))
        if (data['org'],data['repo'],data['name'],data['version'])!=(org_id,repo_id,repo.full_name,row.version):raise ValueError()
        return repo,data['token'],row.version
    except (InvalidToken,ValueError,KeyError,TypeError):raise ValueError('Private repository credential cannot be read; reconnect it securely.') from None


def failure(response):
    status=response.status_code
    if status==429 or status==403 and (response.headers.get('x-ratelimit-remaining')=='0' or 'retry-after' in response.headers):
        return 'GitHub rate limit reached; wait before retrying. No automatic retry was made.'
    if status in (401,403):return 'GitHub credential expired, revoked, or missing required repository permissions.'
    if status in (404,422):return 'GitHub repository or revision unavailable; verify access, repository name and selected ref.'
    return 'GitHub service unavailable; retry later.'


async def api(token,name,suffix='',params=None):
    if not NAME.fullmatch(name):raise ValueError('Invalid repository name')
    if suffix and not re.fullmatch(r'/(branches|commits)(/[A-Za-z0-9%._-]+)?',suffix):raise ValueError('Unsupported GitHub metadata path')
    url='https://api.github.com/repos/'+name+suffix
    try:
        async with httpx.AsyncClient(follow_redirects=False,timeout=10) as client:
            # Bound even metadata responses; never log provider bodies or URLs.
            async with client.stream('GET',url,params=params,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','Accept-Encoding':'identity','X-GitHub-Api-Version':'2026-03-10'}) as response:
                if response.status_code!=200:raise ValueError(failure(response))
                raw=bytearray()
                async for part in response.aiter_bytes(chunk_size=65536):
                    if len(raw)+len(part)>1_000_000:raise ValueError('GitHub metadata response too large')
                    raw.extend(part)
                try:return json.loads(raw)
                except (ValueError,UnicodeError):raise ValueError('GitHub metadata response was invalid') from None
    except httpx.HTTPError:raise ValueError('GitHub network request failed; retry later.') from None


async def verify(token,name):
    metadata=await api(token,name)
    if not isinstance(metadata,dict) or metadata.get('private') is not True or str(metadata.get('full_name','')).lower()!=name.lower():
        raise ValueError('This connection requires a private repository matching the entered owner/name.')
    branches=await api(token,name,'/branches',{'per_page':1})
    if not isinstance(branches,list):raise ValueError('GitHub branch response was invalid')


async def revisions(token,name,kind,ref='',page=1):
    if kind not in ('branches','commits') or not 1<=page<=20:raise ValueError('Invalid revision request')
    params={'per_page':50,'page':page}
    if ref:params['sha']=valid_ref(ref)
    rows=await api(token,name,'/'+kind,params)
    if not isinstance(rows,list):raise ValueError('GitHub revision response was invalid')
    result=[]
    for row in rows[:50]:
        if not isinstance(row,dict):continue
        commit=row.get('commit')
        sha=row.get('sha') if kind=='commits' else commit.get('sha') if isinstance(commit,dict) else None
        if isinstance(sha,str) and re.fullmatch(r'[a-fA-F0-9]{40}(?:[a-fA-F0-9]{24})?',sha):
            result.append({'sha':sha,**({'name':str(row.get('name',''))[:120]} if kind=='branches' else {})})
    return {'items':result,'page':page,'possibly_more':len(rows)>=50}


async def calculate(db_factory,scan):
    payload=json.loads(scan.payload)
    with db_factory() as db:
        repo,token,_=credential(db,scan.org_id,payload['private_repository_id'],payload['credential_version'])
        name=repo.full_name
    resolved={}
    for label,ref in [('head',scan.head_ref),('base',scan.base_ref)]:
        if not ref:continue
        record=await api(token,name,'/commits/'+quote(valid_ref(ref),safe=''))
        sha=record.get('sha') if isinstance(record,dict) else None
        if not isinstance(sha,str) or not re.fullmatch(r'[a-fA-F0-9]{40}(?:[a-fA-F0-9]{24})?',sha):raise ValueError('GitHub did not resolve an immutable revision')
        resolved[label]=sha
    files=await download('https://github.com/'+name,resolved['head'],token=token)
    old=await download('https://github.com/'+name,resolved['base'],token=token) if 'base' in resolved else None
    from .analyzer import analyze
    result=analyze(files,old);result['source_revisions']=resolved
    result['coverage']['baseline_skipped']=getattr(old,'skipped',[])
    result['revision_limitation']='Inputs resolved through authorized GitHub API calls to the recorded immutable commit SHAs.'
    return result


def cancel_jobs(db,org_id,repo_id):
    from sqlalchemy import select
    from .db import Scan
    for scan in db.scalars(select(Scan).where(Scan.org_id==org_id,Scan.status.in_(['queued','running'])).with_for_update()):
        try:matches=json.loads(scan.payload or '{}').get('private_repository_id')==repo_id
        except ValueError:matches=False
        if matches:
            scan.status='cancelled';scan.payload=None;scan.lease=None;scan.updated_at=time.time()
