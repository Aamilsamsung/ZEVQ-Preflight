"""Fixed GitHub origins only. Streams are bounded before archive parsing."""
import re
from urllib.parse import urlparse, quote
import httpx
from .analyzer import MAX_BYTES, read_zip

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


async def download(repo, branch):
    url = archive_url(repo, branch)
    async with httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(25), headers={'Accept-Encoding': 'identity', 'User-Agent': 'ZEVQ-Preflight/0.2'}) as client:
        for attempt in range(2):
            async with client.stream('GET', url) as response:
                if response.status_code in (301, 302, 303, 307, 308) and attempt == 0:
                    url = response.headers.get('location', '')
                    p = urlparse(url)
                    if p.scheme != 'https' or p.hostname != 'codeload.github.com' or p.port is not None or p.username or p.password:
                        raise ValueError('Unexpected archive redirect')
                    continue
                if response.status_code != 200:
                    raise ValueError(f'GitHub archive unavailable (HTTP {response.status_code}); check public access, ref and rate limits')
                data = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(data) + len(chunk) > MAX_BYTES:
                        raise ValueError('Repository archive is too large')
                    data.extend(chunk)
                return read_zip(bytes(data))
    raise ValueError('Archive redirect limit exceeded')
