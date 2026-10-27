import copy
import json
import pytest
from app.contracts import compare_openapi
from app.analyzer import analyze


def document(schema=None, direction='request'):
    op = {'responses': {'200': {'description': 'OK'}}}
    if schema is not None:
        body = {'content': {'application/json': {'schema': schema}}}
        if direction == 'request':
            op['requestBody'] = body
        else:
            op['responses']['200'].update(body)
    return {'openapi': '3.0.3', 'paths': {'/items': {'post': op}}}


def rules(base, head):
    return {f['rule'] for f in compare_openapi(base, head)}


def test_endpoint_removal():
    a = document()
    b = document()
    b['paths'] = {}
    assert 'OAS.ENDPOINT_REMOVED' in rules(a, b)


def test_identical_contract():
    assert compare_openapi(document(), document()) == []


def test_added_endpoint_is_nonbreaking():
    a = document()
    b = document()
    b['paths']['/health'] = {'get': {'responses': {'200': {'description': 'OK'}}}}
    result = compare_openapi(a, b)
    assert len(result) == 1
    assert result[0]['classification'] == 'non-breaking'
    assert result[0]['severity'] == 'info'


@pytest.mark.parametrize('direction,old,new,breaking', [
    ('request', ['a', 'b'], ['a'], True),
    ('request', ['a'], ['a', 'b'], False),
    ('response', ['a'], ['a', 'b'], True),
    ('response', ['a', 'b'], ['a'], False),
])
def test_enum_variance(direction, old, new, breaking):
    result = rules(document({'type': 'string', 'enum': old}, direction), document({'type': 'string', 'enum': new}, direction))
    assert ('OAS.ENUM' in result) is breaking


@pytest.mark.parametrize('direction,old,new,breaking', [
    ('request', [], ['id'], True), ('request', ['id'], [], False),
    ('response', ['id'], [], True), ('response', [], ['id'], False),
])
def test_required_variance(direction, old, new, breaking):
    a = {'type': 'object', 'properties': {'id': {'type': 'integer'}}, 'required': old}
    b = dict(a, required=new)
    assert ('OAS.REQUIRED' in rules(document(a, direction), document(b, direction))) is breaking


def test_local_reference_changes_resolved():
    a = document({'$ref': '#/components/schemas/Item'})
    a['components'] = {'schemas': {'Item': {'type': 'string', 'enum': ['a', 'b']}}}
    b = copy.deepcopy(a)
    b['components']['schemas']['Item']['enum'] = ['a']
    assert 'OAS.ENUM' in rules(a, b)


def test_remote_reference_unknown_not_fetched():
    a = document({'$ref': 'http://169.254.169.254/secrets'})
    assert 'OAS.SCHEMA_UNKNOWN' in rules(a, a)


def test_recursive_reference_unknown():
    a = document({'$ref': '#/components/schemas/Self'})
    a['components'] = {'schemas': {'Self': {'$ref': '#/components/schemas/Self'}}}
    assert 'OAS.SCHEMA_UNKNOWN' in rules(a, a)


def test_composed_schemas_unknown():
    a = document({'oneOf': [{'type': 'integer'}, {'type': 'string'}]})
    assert 'OAS.SCHEMA_COMPLEX' in rules(a, a)


def test_required_parameter_inherited_from_path():
    a, b = document(), document()
    b['paths']['/items']['parameters'] = [{'in': 'header', 'name': 'X-Version', 'required': True, 'schema': {'type': 'string'}}]
    assert 'OAS.PARAM_REQUIRED' in rules(a, b)


def test_operation_parameter_overrides_path():
    a = document()
    b = document()
    b['paths']['/items']['parameters'] = [{'in': 'query', 'name': 'q', 'required': True}]
    b['paths']['/items']['post']['parameters'] = [{'in': 'query', 'name': 'q', 'required': False}]
    assert 'OAS.PARAM_REQUIRED' not in rules(a, b)


def test_security_change():
    a, b = document(), document()
    b['security'] = [{'apiKey': []}]
    assert 'OAS.SECURITY' in rules(a, b)


def test_body_becomes_required():
    a, b = document({}), document({})
    b['paths']['/items']['post']['requestBody']['required'] = True
    assert 'OAS.BODY_REQUIRED' in rules(a, b)


def test_response_property_removed():
    a = document({'type': 'object', 'properties': {'id': {'type': 'integer'}}}, 'response')
    b = document({'type': 'object', 'properties': {}}, 'response')
    assert 'OAS.PROPERTY_REMOVED' in rules(a, b)


def test_full_analyzer_finds_contract_change():
    base = {'api.json': json.dumps(document({'type': 'string', 'enum': ['a', 'b']}))}
    head = {'api.json': json.dumps(document({'type': 'string', 'enum': ['a']}))}
    assert any(f['rule'] == 'OAS.ENUM' for f in analyze(head, base)['findings'])


def test_unsupported_version_unknown():
    a = document()
    a['openapi'] = '2.0'
    assert 'OAS.UNSUPPORTED' in rules(a, document())


@pytest.mark.parametrize('bad', [None, [], 4, 'wrong', {'type': 'object', 'properties': []}])
def test_malformed_schema_does_not_report_clean(bad):
    a = document({'type': 'object'})
    b = document(bad)
    if bad is None:
        b['paths']['/items']['post']['responses'] = None
    result = compare_openapi(a, b)
    assert result
    assert any(f['classification'] == 'unknown' for f in result)


def test_invalid_proposed_json_with_arbitrary_filename_reported():
    result = analyze({'api.json': '{'}, {'api.json': json.dumps(document())})
    assert any(f['rule'] == 'OAS.INVALID' for f in result['findings'])


def test_removed_contract_is_inconclusive_not_silent():
    result = analyze({}, {'api.json': json.dumps(document())})
    assert any(f['rule'] == 'OAS.DOCUMENT_REMOVED' for f in result['findings'])
