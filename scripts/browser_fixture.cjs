'use strict';
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
function readFixture(value) {
  let data;
  try { data = JSON.parse(value || ''); } catch { throw Error('A valid PREFLIGHT_HOSTED_BROWSER_FIXTURE Actions secret is required; never paste credentials into chat.'); }
  if (data?.authorized_synthetic_qa !== true || typeof data.email !== 'string'
      || !/^qa-[a-z0-9._-]+@example\.test$/i.test(data.email)
      || typeof data.password !== 'string' || data.password.length < 14 || data.password.length > 256
      || !UUID.test(data.organization_id || '') || !UUID.test(data.review_scan_id || '')) {
    throw Error('Only an explicitly authorized synthetic QA identity and organization/report UUIDs are accepted.');
  }
  return Object.freeze(data);
}
module.exports = { readFixture };
