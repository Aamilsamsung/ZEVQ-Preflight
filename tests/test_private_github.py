import asyncio
import io
import json
import logging
import zipfile
import pytest
import httpx
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_api import env,login
from app import private_github as private,github
from app.db import Repository,RepositoryCredential,Scan
from app.worker import claim,execute

TOKEN='github_pat_'+ 'SYNTHETIC_TOKEN_'*3
SHA_A='a'*40
SHA_B='b'*40


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv('PREFLIGHT_PRIVATE_GITHUB_ENABLED','1');monkeypatch.setenv('PREFLIGHT_CREDENTIAL_KEY',Fernet.generate_key().decode())
    seen=[];original=httpx.AsyncClient
    def handler(r):
        seen.append(r)
        if r.url.host=='api.github.com':assert r.headers.get('authorization')=='Bearer '+TOKEN
        if r.url.path.endswith('/branches'):return httpx.Response(200,json=[{'name':'main','commit':{'sha':SHA_B}}])
        if '/commits/' in r.url.path:return httpx.Response(200,json={'sha':SHA_A if r.url.path.endswith('/base') else SHA_B})
        if r.url.path.endswith('/commits'):return httpx.Response(200,json=[{'sha':SHA_B,'commit':{'message':'PRIVATE_MESSAGE_DO_NOT_RETURN'}}])
        if '/zipball/' in r.url.path:return httpx.Response(302,headers={'location':'https://codeload.github.com/o/private/legacy.zip/'+r.url.path.split('/')[-1]+'?token=TEMPORARY_SIGNED_SECRET'})
        if r.url.host=='codeload.github.com':
            assert 'authorization' not in r.headers
            b=io.BytesIO()
            with zipfile.ZipFile(b,'w') as z:z.writestr('root/api.py','def removed():\n return 1\n' if SHA_A in str(r.url) else 'def replacement():\n return 1\n')
            return httpx.Response(200,content=b.getvalue())
        return httpx.Response(200,json={'private':True,'full_name':'o/private'})
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    return seen


def connect(c,org,h):return c.post(f'/api/orgs/{org}/private-github/repos',headers=h,json={'full_name':'o/private','token':TOKEN})


def test_default_disabled_and_classic_credentials_rejected(env,monkeypatch):
    _,c,(org,*_)=env;h=login(c);monkeypatch.delenv('PREFLIGHT_PRIVATE_GITHUB_ENABLED',raising=False)
    assert c.get(f'/api/orgs/{org}/private-github/status').json()['enabled'] is False
    assert connect(c,org,h).status_code==422


def test_encrypted_binding_and_no_export_of_credentials(env,provider):
    app,c,(org,*_)=env;h=login(c);r=connect(c,org,h);assert r.status_code==201;rid=r.json()['id']
    with app.state.db() as db:
        row=db.get(RepositoryCredential,rid);assert TOKEN not in row.ciphertext
        repo,token,version=private.credential(db,org,rid);assert token==TOKEN and version==1
    for path in [f'/api/orgs/{org}/repos','/api/auth/export',f'/api/orgs/{org}/audit']:
        out=c.get(path);assert out.status_code==200 and TOKEN not in out.text and 'ciphertext' not in out.text


def test_roles_csrf_and_tenant_isolation(env,provider):
    app,c,(org,foreign,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    viewer=TestClient(app);vh=login(viewer,'viewer@example.test')
    assert connect(viewer,org,vh).status_code==403
    assert connect(c,org,{}).status_code==403
    assert connect(c,foreign,h).status_code==404
    assert c.get(f'/api/orgs/{foreign}/repos/{rid}/revisions/branches').status_code==404
    assert c.delete(f'/api/orgs/{foreign}/repos/{rid}/credential',headers=h).status_code==404
    with app.state.db() as db:
        with pytest.raises(ValueError):private.credential(db,foreign,rid)


def test_credential_swap_between_organizations_fails_closed(env,provider):
    app,c,(org,foreign,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    with app.state.db() as db:
        original=db.get(RepositoryCredential,rid)
        repo=Repository(org_id=foreign,full_name='o/other',source_kind='private');db.add(repo);db.flush()
        db.add(RepositoryCredential(repo_id=repo.id,org_id=foreign,ciphertext=original.ciphertext,version=1));db.commit()
        with pytest.raises(ValueError,match='cannot be read'):private.credential(db,foreign,repo.id)


def test_private_scan_resolves_shas_and_emits_real_evidence(env,provider,caplog):
    app,c,(org,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    r=c.post(f'/api/orgs/{org}/scans',headers=h,json={'repository_id':rid,'base_ref':'base','head_ref':'main'});assert r.status_code==202
    with app.state.db() as db:assert TOKEN not in db.get(Scan,r.json()['id']).payload
    job=claim(app.state.db)
    with caplog.at_level(logging.INFO):execute(app.state.db,*job)
    result=c.get(f'/api/orgs/{org}/scans/{r.json()["id"]}').json()
    assert result['status']=='completed'
    assert result['result']['source_revisions']=={'base':SHA_A,'head':SHA_B}
    assert any(f['rule']=='PY.FUNCTION_REMOVED' for f in result['result']['findings'])
    assert TOKEN not in caplog.text and 'TEMPORARY_SIGNED_SECRET' not in caplog.text
    for path in ['report','report?format=csv']:
        out=c.get(f'/api/orgs/{org}/scans/{r.json()["id"]}/'+path)
        assert out.status_code==200 and TOKEN not in out.text


def test_branch_and_commit_listing_is_scoped_and_bounded(env,provider):
    _,c,(org,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    branches=c.get(f'/api/orgs/{org}/repos/{rid}/revisions/branches').json();assert branches['items']==[{'name':'main','sha':SHA_B}]
    commits=c.get(f'/api/orgs/{org}/repos/{rid}/revisions/commits?ref=main');assert commits.json()['items']==[{'sha':SHA_B}]
    assert 'PRIVATE_MESSAGE' not in commits.text
    assert c.get(f'/api/orgs/{org}/repos/{rid}/revisions/commits?page=21').status_code==422
    assert c.get(f'/api/orgs/{org}/repos/{rid}/revisions/unknown').status_code==422


def test_disconnect_cancels_jobs_and_prevents_late_publication(env,provider):
    app,c,(org,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    scan=c.post(f'/api/orgs/{org}/scans',headers=h,json={'repository_id':rid}).json();job=claim(app.state.db)
    assert c.delete(f'/api/orgs/{org}/repos/{rid}/credential',headers=h).json()['provider_revocation_required']
    execute(app.state.db,*job)
    with app.state.db() as db:
        assert db.get(RepositoryCredential,rid) is None
        row=db.get(Scan,scan['id']);assert row.status=='cancelled' and row.result is None and row.payload is None
    assert c.post(f'/api/orgs/{org}/scans',headers=h,json={'repository_id':rid}).status_code==409


def test_rotation_cancels_queued_jobs_and_invalidates_old_version(env,provider):
    app,c,(org,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    scan=c.post(f'/api/orgs/{org}/scans',headers=h,json={'repository_id':rid}).json()
    assert connect(c,org,h).status_code==201
    with app.state.db() as db:
        assert db.get(Scan,scan['id']).status=='cancelled'
        with pytest.raises(ValueError,match='changed'):private.credential(db,org,rid,1)


@pytest.mark.parametrize('status',[401,403,404,422,429,503])
def test_provider_error_bodies_never_echoed(env,provider,monkeypatch,status):
    _,c,(org,*_)=env;h=login(c);original=httpx.AsyncClient
    # provider fixture already patched; use a fresh saved class from httpx module implementation.
    from httpx._client import AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(status,text='PRIVATE_PROVIDER_SECRET')),**kw))
    r=connect(c,org,h);assert r.status_code==422 and 'PRIVATE_PROVIDER_SECRET' not in r.text and TOKEN not in r.text


def test_no_credentials_forwarded_to_redirect_host(provider):
    asyncio.run(github.download('https://github.com/o/private',SHA_B,token=TOKEN))
    assert len(provider)==2 and provider[0].headers.get('authorization') and 'authorization' not in provider[1].headers


def test_classic_token_and_invalid_key_never_contact_github(env,provider,monkeypatch):
    _,c,(org,*_)=env;h=login(c)
    for token in ['ghp_'+'X'*40,'github_pat_'+'X'*300]:
        assert c.post(f'/api/orgs/{org}/private-github/repos',headers=h,json={'full_name':'o/private','token':token}).status_code==422
    assert provider==[]
    monkeypatch.setenv('PREFLIGHT_CREDENTIAL_KEY','broken')
    assert connect(c,org,h).status_code==422 and provider==[]


def test_token_rotation_key_loss_fails_closed(env,provider,monkeypatch):
    app,c,(org,*_)=env;h=login(c);rid=connect(c,org,h).json()['id']
    monkeypatch.setenv('PREFLIGHT_CREDENTIAL_KEY',Fernet.generate_key().decode())
    assert c.post(f'/api/orgs/{org}/scans',headers=h,json={'repository_id':rid}).status_code==409


def test_api_rate_limit_single_request_and_no_body_disclosure(env,provider,monkeypatch):
    _,c,(org,*_)=env;h=login(c);seen=[]
    from httpx._client import AsyncClient
    def handler(r):seen.append(r);return httpx.Response(403,headers={'x-ratelimit-remaining':'0'},text=TOKEN)
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:AsyncClient(transport=httpx.MockTransport(handler),**kw))
    out=connect(c,org,h);assert out.status_code==422 and 'rate limit' in out.text and TOKEN not in out.text and len(seen)==1


def test_private_archive_rejects_untrusted_redirect(env,provider,monkeypatch):
    from httpx._client import AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={'location':'https://evil.test/source?secret='+TOKEN})),**kw))
    with pytest.raises(ValueError,match='Unexpected archive redirect'):asyncio.run(github.download('https://github.com/o/private','main',token=TOKEN))


def test_malformed_redirect_port_cannot_expose_credential(env,provider,monkeypatch):
    from httpx._client import AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(302,headers={'location':'https://codeload.github.com:'+TOKEN+'/x'})),**kw))
    with pytest.raises(ValueError,match='GitHub network or archive response') as error:asyncio.run(github.download('https://github.com/o/private','main',token=TOKEN))
    assert TOKEN not in str(error.value)


def test_invalid_revision_shapes_do_not_claim_immutable_shas(provider,monkeypatch):
    from httpx._client import AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=[{'name':'bad','commit':'invalid'},{'name':'wrong-length','commit':{'sha':'a'*41}}])),**kw))
    data=asyncio.run(private.revisions(TOKEN,'o/private','branches'));assert data['items']==[]
