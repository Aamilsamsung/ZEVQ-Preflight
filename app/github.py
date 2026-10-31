"""Fixed GitHub origins only. Streams are bounded before archive parsing."""
import re
import logging
from urllib.parse import urlparse, quote
import httpx
from .analyzer import MAX_BYTES, read_zip

# HTTPX INFO messages include full redirect URLs, which can be signed credentials.
logging.getLogger('httpx').setLevel(logging.WARNING)

REF = re.compile(r'[A-Za-z0-9._/-]{1,120}')
NAME = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9_.-]{1,100}')


def valid_ref(ref):
    if not REF.fullmatch(ref) or '..' in ref or ref.startswith('/') or ref.endswith('/'):
        raise ValueError('Invalid Git reference')
    return ref


def archive_url(url, branch):
    p = urlparse(url)
    if p.scheme != 'https' or p.hostname != 'github.com' or p.port is not None or p.query or p.fragment or p.username or p.password:
        raise ValueError('Only HTTPS github.com repository URLs are supported')
    name = p.path.strip('/')
    if not NAME.fullmatch(name):
        raise ValueError('Enter github.com/owner/repo')
    return 'https://api.github.com/repos/' + name + '/zipball/' + quote(valid_ref(branch), safe='')


def http_failure(response, stage='archive'):
    status=response.status_code
    if status==429 or (status==403 and (response.headers.get('x-ratelimit-remaining')=='0' or 'retry-after' in response.headers)):
        return f'GitHub rate limit reached (HTTP {status}); wait before retrying. No automatic retry was made.'
    if status in (401,403):return f'GitHub {stage} access denied (HTTP {status}); check permissions or provider policy. Private access is not configured.'
    if status>=500:return f'GitHub {stage} service failure (HTTP {status}); retry later.'
    return f'GitHub {stage} unavailable (HTTP {status})'


async def diagnose_404(client, original_url, redirected):
    prefix,ref=original_url.rsplit('/zipball/',1)
    stage='archive download host' if redirected else 'archive API'
    try:
        async with client.stream('GET',prefix,timeout=5) as repo:
            if repo.status_code==404:
                return 'GitHub repository not publicly accessible (HTTP 404). Missing and private repositories cannot be distinguished without authorization; private access is not configured.'
            if repo.status_code!=200:return http_failure(repo,'repository metadata')
        async with client.stream('GET',prefix+'/commits/'+ref,timeout=5) as commit:
            if commit.status_code==404:return 'GitHub revision not found (HTTP 404) in a confirmed public repository; check the exact branch, tag or commit SHA.'
            if commit.status_code==422:return 'GitHub revision could not be resolved (HTTP 422) in a confirmed public repository; check the exact branch, tag or commit SHA.'
            if commit.status_code!=200:return http_failure(commit,'revision lookup')
        return f'GitHub {stage} returned HTTP 404 although the public repository and revision resolved; archive retrieval failed. Retry later or upload a permitted ZIP.'
    except httpx.HTTPError:
        return f'GitHub {stage} returned HTTP 404; repository/revision diagnostics were inconclusive due to a network error. Missing/private access is not established.'


async def download(repo, branch, token=None):
    try:
        return await _download(repo, branch, token)
    except (httpx.HTTPError, httpx.InvalidURL):
        # HTTPX may parse a malformed Location before returning the response.
        # Its exception can contain signed URLs or credentials; never echo it.
        raise ValueError('GitHub network or archive response unavailable; retry later.') from None


async def _download(repo, branch, token=None):
    url = archive_url(repo, branch)
    original_url=url
    async with httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(25), headers={'Accept-Encoding': 'identity', 'User-Agent': 'ZEVQ-Preflight/0.2'}) as client:
        for attempt in range(2):
            async with client.stream('GET', url, headers={'Authorization':'Bearer '+token} if token and urlparse(url).hostname=='api.github.com' else {}) as response:
                if response.status_code in (301, 302, 303, 307, 308) and attempt == 0:
                    url = response.headers.get('location', '')
                    try:
                        p = urlparse(url)
                        safe = p.scheme == 'https' and p.hostname == 'codeload.github.com' and p.port is None and not p.username and not p.password
                    except ValueError:
                        safe = False
                    if not safe:
                        raise ValueError('Unexpected archive redirect')
                    continue
                if response.status_code != 200:
                    if token:
                        from .private_github import failure
                        message=failure(response)
                    else:
                        message=await diagnose_404(client,original_url,attempt>0) if response.status_code==404 else http_failure(response)
                    raise ValueError(message)
                data = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(data) + len(chunk) > MAX_BYTES:
                        raise ValueError('Repository archive is too large')
                    data.extend(chunk)
                return read_zip(bytes(data))
    raise ValueError('Archive redirect limit exceeded')
