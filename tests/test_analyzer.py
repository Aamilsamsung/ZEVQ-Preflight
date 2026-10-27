import io
import zipfile
import pytest
from app.analyzer import analyze, read_zip
from app.main import archive_url

def test_removed_api_endpoint():
    old={'api.py':'@app.get("/orders")\ndef read(): pass'}
    new={'api.py':'@app.get("/items")\ndef read(): pass'}
    r=analyze(new,old)
    assert r['risk_level']=='high'
    assert any('GET /orders' in f['message'] for f in r['findings'])

def test_syntax_detection():
    assert analyze({'broken.py':'def x(\n'})['risk_level']=='high'

def test_valid_source():
    assert analyze({'app.py':'@app.get("/health")\ndef health(): return 1'})['routes_detected']==['GET /health']

def test_zip():
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w') as z: z.writestr('project/app.py','print("hello")')
    assert len(read_zip(mem.getvalue()))==1

@pytest.mark.parametrize('url',['http://github.com/x/y','https://example.com/x/y','https://github.com/x/y?key=1'])
def test_reject_url(url):
    with pytest.raises(ValueError): archive_url(url,'main')
