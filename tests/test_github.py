import asyncio
import httpx
import pytest
from app import github

class Stream(httpx.AsyncByteStream):
    async def __aiter__(self):
        yield b'x' * 65536
        yield b'y' * 65536

@pytest.mark.parametrize('redirect',['http://codeload.github.com/x','https://evil.test/x','https://user:pass@codeload.github.com/x','https://codeload.github.com:443/x'])
def test_unsafe_redirect(monkeypatch,redirect):
    original=httpx.AsyncClient
    transport=httpx.MockTransport(lambda r: httpx.Response(302,headers={'location':redirect}))
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kw: original(transport=transport,**kw))
    with pytest.raises(ValueError,match='Unexpected archive redirect'):
        asyncio.run(github.download('https://github.com/o/r','main'))

def test_download_bounded(monkeypatch):
    original=httpx.AsyncClient
    transport=httpx.MockTransport(lambda r: httpx.Response(200,stream=Stream()))
    monkeypatch.setattr(github,'MAX_BYTES',70000)
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kw: original(transport=transport,**kw))
    with pytest.raises(ValueError,match='too large'):
        asyncio.run(github.download('https://github.com/o/r','main'))

@pytest.mark.parametrize('status',[403,404,429,500])
def test_download_http_failure(monkeypatch,status):
    original=httpx.AsyncClient
    transport=httpx.MockTransport(lambda r: httpx.Response(status))
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kw: original(transport=transport,**kw))
    with pytest.raises(ValueError,match=f'HTTP {status}'):
        asyncio.run(github.download('https://github.com/o/r','main'))

@pytest.mark.parametrize('metadata,revision,expected',[(404,404,'Missing and private'),(200,404,'revision not found'),(200,200,'archive retrieval failed'),(403,200,'access denied')])
def test_404_diagnostics_are_evidence_based(monkeypatch,metadata,revision,expected):
    original=httpx.AsyncClient;seen=[]
    def handler(request):
        seen.append(str(request.url))
        if '/zipball/' in request.url.path:return httpx.Response(404)
        return httpx.Response(revision if '/commits/' in request.url.path else metadata)
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    with pytest.raises(ValueError,match=expected):asyncio.run(github.download('https://github.com/o/r','feature/test'))
    assert all(url.startswith('https://api.github.com/repos/o/r') for url in seen)
    assert len(seen)<=3

@pytest.mark.parametrize('status,headers',[(429,{}),(403,{'x-ratelimit-remaining':'0'}),(403,{'retry-after':'60'})])
def test_rate_limit_stops_without_retry_or_diagnostics(monkeypatch,status,headers):
    original=httpx.AsyncClient;seen=[]
    def handler(request):seen.append(request);return httpx.Response(status,headers=headers)
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    with pytest.raises(ValueError,match='rate limit'):asyncio.run(github.download('https://github.com/o/r','main'))
    assert len(seen)==1

def test_codeload_failure_is_distinct_and_bodies_not_echoed(monkeypatch):
    original=httpx.AsyncClient
    def handler(r):
        if '/zipball/' in r.url.path:return httpx.Response(302,headers={'location':'https://codeload.github.com/o/r/legacy.zip/main'})
        return httpx.Response(404 if r.url.host=='codeload.github.com' else 200,text='SYNTHETIC_PRIVATE_PROVIDER_BODY')
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    with pytest.raises(ValueError) as error:asyncio.run(github.download('https://github.com/o/r','main'))
    assert 'archive download host' in str(error.value) and 'SYNTHETIC_PRIVATE_PROVIDER_BODY' not in str(error.value)
