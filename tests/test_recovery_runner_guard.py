import pytest
from scripts.hosted_recovery_acceptance import snapshot_url, SNAPSHOT_HOST


def test_only_explicit_snapshot_endpoint_allowed_and_tls_verified():
    value = snapshot_url(f'postgresql://fixture:fixture@{SNAPSHOT_HOST}/neondb?sslmode=require')
    assert 'sslmode=verify-full' in value


@pytest.mark.parametrize('value', [
    'postgresql://fixture:fixture@ep-lingering-glade-b3vgftj2.c-4.ap-southeast-1.aws.neon.tech/neondb',
    'postgresql://fixture:fixture@localhost/neondb',
    f'postgresql://fixture:fixture@{SNAPSHOT_HOST}/another',
    f'postgresql://{SNAPSHOT_HOST}/neondb',
    '',
])
def test_live_unknown_or_missing_endpoint_rejected_before_connect(value):
    with pytest.raises(ValueError):
        snapshot_url(value)
