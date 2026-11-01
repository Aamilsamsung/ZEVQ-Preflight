'use strict';
const assert = require('node:assert/strict');
const { readFixture } = require('./browser_fixture.cjs');
const fixture = { authorized_synthetic_qa: true, email: 'qa-browser@example.test', password: 'fixture-only-long-password', organization_id: '00000000-0000-0000-0000-000000000001', review_scan_id: '00000000-0000-0000-0000-000000000002' };
assert.equal(readFixture(JSON.stringify(fixture)).email, fixture.email);
for (const value of ['', 'not-json', JSON.stringify({ ...fixture, authorized_synthetic_qa: false }), JSON.stringify({ ...fixture, email: 'real-user@example.com' }), JSON.stringify({ ...fixture, organization_id: '../other' }), JSON.stringify({ ...fixture, review_scan_id: '' }), JSON.stringify({ ...fixture, password: 'short' })]) {
  assert.throws(() => readFixture(value), error => !error.message.includes(fixture.password));
}
console.log('Browser fixture: 8 validation/redaction checks passed.');
