/* Actual notification transport drill. Never changes service health or production incidents. */
'use strict';
const assert = require('node:assert/strict');
const { probe, run } = require('./external_monitor.cjs');
const canonical = 'ZEVQ staging operational monitor incident';
async function drill(github, context, { healthProbe = probe } = {}) {
  assert.equal(context.repo.owner, 'Aamilsamsung');
  assert.equal(context.repo.repo, 'ZEVQ-Preflight');
  assert.equal(context.runAttempt ?? Number(process.env.GITHUB_RUN_ATTEMPT || 0), 1, 'Do not automatically repeat a notification drill');
  const title = '[SYNTHETIC DRILL ' + context.runId + '] ZEVQ incident and recovery notifications';
  const report = { title, scope: 'Synthetic detection with real GitHub issue/comment transport; no application outage', issue: null, recovered: false, inbox_receipt: 'NOT VERIFIED' };
  async function guard() {
    const branch = await github.rest.repos.getBranch({ ...context.repo, branch: 'implementation/public-onboarding-20261029' });
    assert.equal(branch.data.commit.sha, context.sha, 'Concurrent branch activity detected; stop all mutations');
  }
  await guard();
  assert.equal(await healthProbe(), true, 'Hosted health must be verified before a synthetic drill');
  const issues = github.rest.issues;
  const wrapper = { rest: { issues: {
    listForRepo: async args => {
      const response = await issues.listForRepo(args);
      return { ...response, data: response.data.filter(i => i.title === title).map(i => ({ ...i, title: canonical })) };
    },
    create: async args => {
      await guard();
      const response = await issues.create({ ...args, title, body: '**SYNTHETIC TEST — no production outage was induced.**\n\nThis owner-authorized drill tests real incident notification transport using simulated failed probes.\n\n' + args.body });
      report.issue = { number: response.data.number, url: response.data.html_url };
      return response;
    },
    createComment: async args => {
      await guard();
      return issues.createComment({ ...args, body: '**SYNTHETIC TEST RECOVERY.** The actual hosted health probe is healthy. This verifies the recovery transport for the drill, not resolution of a real outage.\n\n' + args.body });
    },
    update: async args => {
      await guard();
      const response = await issues.update(args);
      report.recovered = response.data.state === 'closed';
      return response;
    }
  } } };
  const previous = process.env.PREFLIGHT_MONITOR_ENABLED;
  process.env.PREFLIGHT_MONITOR_ENABLED = 'true';
  try {
    await run(wrapper, context, { probeFn: async () => false, pause: async () => {} });
    assert.ok(report.issue, 'Incident transport did not create the drill issue');
    await run(wrapper, context, { probeFn: healthProbe, pause: async () => {} });
    assert.equal(report.recovered, true, 'Actual healthy probe did not close the synthetic incident');
    return report;
  } finally {
    if (previous === undefined) delete process.env.PREFLIGHT_MONITOR_ENABLED;
    else process.env.PREFLIGHT_MONITOR_ENABLED = previous;
  }
}
module.exports = { drill };
