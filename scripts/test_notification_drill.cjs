'use strict';
const assert = require('node:assert/strict');
const { drill } = require('./notification_drill.cjs');
(async () => {
  const context = { repo: { owner: 'Aamilsamsung', repo: 'ZEVQ-Preflight' }, sha: 'expected', runId: 123, runAttempt: 1 };
  let rows = [], mutations = 0, guards = 0;
  const github = { rest: {
    repos: { getBranch: async () => { guards++; return { data: { commit: { sha: 'expected' } } }; } },
    issues: {
      listForRepo: async () => ({ data: [] }), // deliberately stale index
      get: async args => { assert.equal(args.issue_number, 1); return { data: rows[0] }; },
      create: async args => { mutations++; assert.match(args.title, /SYNTHETIC DRILL/); assert.match(args.body, /no production outage/); const data = { ...args, number: 1, html_url: 'https://example.test/drill', state: 'open' }; rows.push(data); return { data }; },
      createComment: async args => { mutations++; assert.match(args.body, /SYNTHETIC TEST RECOVERY/); return { data: {} }; },
      update: async args => { mutations++; rows[0].state = args.state; return { data: rows[0] }; }
    }
  } };
  const result = await drill(github, context, { healthProbe: async () => true });
  assert.equal(result.recovered, true); assert.equal(mutations, 3); assert.equal(guards, 4); assert.equal(result.inbox_receipt, 'NOT VERIFIED');
  mutations = 0;
  await assert.rejects(() => drill(github, { ...context, sha: 'newer' }, { healthProbe: async () => true }), /Concurrent branch/);
  assert.equal(mutations, 0);
  await assert.rejects(() => drill(github, context, { healthProbe: async () => false }), /Hosted health/);
  assert.equal(mutations, 0);
  await assert.rejects(() => drill(github, { ...context, runAttempt: 2 }, { healthProbe: async () => true }), /Do not automatically repeat/);
  console.log('Notification drill: 4 deterministic checks passed; inbox receipt requires real verification.');
})().catch(e => { console.error(e); process.exitCode = 1; });
