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


def zip_bytes(entries):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        for name, value in entries:
            archive.writestr(name, value)
    return data.getvalue()


@pytest.mark.parametrize('path', ['../evil.py', '/evil.py', 'C:/evil.py', 'a\\evil.py'])
def test_zip_rejects_unsafe_paths(path):
    with pytest.raises(ValueError, match='Unsafe'):
        read_zip(zip_bytes([(path, 'x = 1')]))


def test_zip_symlink_rejected():
    info = zipfile.ZipInfo('link.py')
    info.external_attr = 0o120777 << 16
    with pytest.raises(ValueError, match='symlink'):
        read_zip(zip_bytes([(info, 'target.py')]))


def test_zip_oversized_file_is_disclosed():
    sources = read_zip(zip_bytes([('root/ok.py', 'x = 1'), ('root/huge.py', 'x' * 300001)]))
    assert list(sources) == ['ok.py']
    result = analyze(sources)
    assert result['coverage']['skipped'][0]['reason'] == 'file-size-limit'


def test_zip_duplicate_rejected():
    with pytest.warns(UserWarning):
        archive = zip_bytes([('a.py', 'x=1'), ('a.py', 'x=2')])
    with pytest.raises(ValueError, match='Duplicate'):
        read_zip(archive)


def test_zip_invalid_rejected():
    with pytest.raises(ValueError, match='Invalid'):
        read_zip(b'not a zip')


def test_comments_and_strings_are_not_routes_or_dangerous_calls():
    source = '# @app.get("/fake")\ns = "eval(x)"\n'
    report = analyze({'a.py': source})
    assert report['routes_detected'] == []
    assert report['findings'] == []


def test_keyword_route_and_async_handler():
    source = '@router.post(path="/orders")\nasync def create(): pass'
    assert analyze({'a.py': source})['routes_detected'] == ['POST /orders']


def test_signatures_and_removals_have_evidence():
    base = {'a.py': 'def removed(x): pass\ndef changed(x): pass'}
    head = {'a.py': 'def changed(x, y): pass'}
    result = analyze(head, base)
    assert {f['rule'] for f in result['findings']} == {'PY.FUNCTION_REMOVED', 'PY.SIGNATURE_CHANGED'}
    for f in result['findings']:
        assert all(k in f for k in ('id', 'line', 'evidence', 'confidence', 'recommended_action', 'rule_version'))
    assert result == analyze(head, base)


def test_syntax_failure_does_not_claim_routes_removed():
    result = analyze({'a.py': 'def broken('}, {'a.py': '@app.get("/a")\ndef old(): pass'})
    assert {f['rule'] for f in result['findings']} == {'PY.SYNTAX', 'SOURCE.COMPARISON_INCOMPLETE'}


def test_security_calls_not_secrets_in_evidence():
    result = analyze({'a.py': 'eval("private-code")\nsubprocess.run("private-command", shell=True)'})
    assert len(result['findings']) == 2
    assert 'private-code' not in str(result)
    assert 'private-command' not in str(result)


def test_no_customer_code_executed(tmp_path):
    marker = tmp_path / 'executed'
    result = analyze({'a.py': f'open({str(marker)!r}, "w").write("oops")'})
    assert not marker.exists()
    assert result['simulation']['status'] == 'not-executed'


def test_javascript_not_silently_reported_as_parsed():
    result = analyze({'a.ts': 'not even valid typescript'})
    assert result['python_files_parsed'] == 0
    assert result['coverage']['files_without_language_analysis'] == ['a.ts']


def test_revision_archive_roots_normalized():
    base = read_zip(zip_bytes([('owner-repo-aaa/app.py', 'def x(): pass')]))
    head = read_zip(zip_bytes([('owner-repo-bbb/app.py', 'def x(): pass')]))
    assert analyze(head, base)['findings'] == []


@pytest.mark.parametrize('content,reason', [('x' * 300001, 'file-size-limit'), (b'\xff', 'non-utf8'), (b'abc\x00', 'binary-content')])
def test_omitted_head_does_not_claim_removed_function_or_route(content, reason):
    old = read_zip(zip_bytes([('old-root/api.py', '@app.get("/x")\ndef handler(): pass'), ('old-root/ok.py', 'x=1')]))
    head = read_zip(zip_bytes([('new-root/api.py', content), ('new-root/ok.py', 'x=1')]))
    assert head.skipped == [{'file': 'api.py', 'reason': reason}]
    result = analyze(head, old)
    assert not any(f['rule'] in {'PY.ROUTE_REMOVED', 'PY.FUNCTION_REMOVED'} for f in result['findings'])
    assert result['coverage']['comparison_unknown_files'] == ['api.py']
    assert result['coverage']['route_removal_checks_complete'] is False
    assert any(f['rule'] == 'SOURCE.COMPARISON_INCOMPLETE' for f in result['findings'])


def test_route_moved_to_omitted_file_not_reported_removed():
    old = {'old.py': '@app.get("/x")\ndef handler(): pass'}
    head = read_zip(zip_bytes([('root/ok.py', 'x=1'), ('root/new.py', b'\xff')]))
    result = analyze(head, old)
    assert not any(f['rule'] == 'PY.ROUTE_REMOVED' for f in result['findings'])


def test_file_count_omission_does_not_claim_removal(monkeypatch):
    import app.analyzer as analyzer
    monkeypatch.setattr(analyzer, 'MAX_FILES', 1)
    head = read_zip(zip_bytes([('root/ok.py', 'x=1'), ('root/api.py', 'def handler(): pass')]))
    result = analyze(head, {'api.py': 'def handler(): pass'})
    assert head.skipped == [{'file': 'api.py', 'reason': 'file-count-limit'}]
    assert not any(f['rule'] == 'PY.FUNCTION_REMOVED' for f in result['findings'])


def test_archive_root_decision_includes_skipped_paths():
    head = read_zip(zip_bytes([('module/api.py', 'x=1'), ('README.md', 'text')]))
    assert 'module/api.py' in head
    assert head.skipped == [{'file': 'README.md', 'reason': 'unsupported-extension'}]


def test_sources_roundtrip_preserves_omission_uncertainty():
    import json
    from app.analyzer import Sources
    source = read_zip(zip_bytes([('root/ok.py', 'x=1'), ('root/api.py', b'\xff')]))
    payload = json.loads(json.dumps({'files': source, 'skipped': source.skipped}))
    restored = Sources()
    restored.update(payload['files'])
    restored.skipped = payload['skipped']
    result = analyze(restored, {'api.py': 'def handler(): pass'})
    assert not any(f['rule'] == 'PY.FUNCTION_REMOVED' for f in result['findings'])
    assert result['coverage']['comparison_unknown_files'] == ['api.py']


def test_zip_rejects_canonical_path_aliases():
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w') as archive:
        archive.writestr('root/app.py', 'x = 1')
        archive.writestr('root/./app.py', 'x = 2')
    with pytest.raises(ValueError, match='Duplicate ZIP path'):
        read_zip(mem.getvalue())
