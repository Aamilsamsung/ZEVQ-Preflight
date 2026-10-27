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
