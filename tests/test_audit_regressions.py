"""Audit regressions: expected failures are open defects, never counted as passes."""
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from app.main import create_app
from app.db import Base, factory, make_engine
from app.security import limit
from app.contracts import compare_openapi

@pytest.mark.xfail(strict=True,reason='AUDIT-02: staging boundary returns before security header middleware')
def test_anonymous_denial_includes_security_headers(tmp_path):
    app=create_app('sqlite:///'+str(tmp_path/'audit.db'),mode='staging')
    Base.metadata.create_all(app.state.engine)
    # No lifespan: exercise the staging middleware with a disposable database.
    client=TestClient(app)
    response=client.get('/api/auth/me')
    assert response.status_code==401
    for name in ['Content-Security-Policy','X-Content-Type-Options','X-Frame-Options','Strict-Transport-Security']:
        assert name in response.headers

@pytest.mark.xfail(strict=True,reason='AUDIT-05: OpenAPI evidence paths are not RFC6901 escaped')
def test_openapi_evidence_pointer_resolves_baseline():
    baseline={'openapi':'3.0.3','paths':{'/orders':{'get':{'responses':{'200':{'description':'OK'}}}}}}
    f=compare_openapi(baseline,{'openapi':'3.0.3','paths':{}})[0]
    target=baseline
    for segment in f['evidence']['pointer'].split('/')[1:]:
        target=target[segment.replace('~1','/').replace('~0','~')]
    assert target==baseline['paths']['/orders']['get']


def test_database_rate_limit_exact_boundary(tmp_path):
    engine=make_engine('sqlite:///'+str(tmp_path/'rate.db'));Base.metadata.create_all(engine);db=factory(engine)
    for _ in range(3):limit(db,'synthetic-audit-key',3,900)
    with pytest.raises(HTTPException) as error:limit(db,'synthetic-audit-key',3,900)
    assert error.value.status_code==429
    assert error.value.headers['Retry-After']=='900'
    # A distinct account does not inherit the first account's counter.
    limit(db,'another-synthetic-key',3,900)
    engine.dispose()
