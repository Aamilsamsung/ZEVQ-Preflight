/* Actual hosted anonymous journeys. Read-only: no login attempts, mail, or data writes. */
'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const Axe = require('@axe-core/playwright').default;
const base = 'https://zevq-preflight-staging.onrender.com';
const out = 'artifacts/hosted-gate';
const results = [], errors = [], accessibility = [];
fs.mkdirSync(out, { recursive: true });
async function main() {
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const page = await context.newPage();
    page.setDefaultTimeout(30000);
    page.on('pageerror', e => errors.push(e.message));
    const statusResponse = await context.request.get(base + '/api/auth/email/status', { timeout: 60000 });
    assert.equal(statusResponse.status(), 200);
    const status = await statusResponse.json();
    assert.equal(status.registration, 'disabled', 'This acceptance run expects protected staging');
    results.push({ feature: 'Actual registration gate remains closed', status: 'PASS' });
    const paths = ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email'];
    for (const width of [390, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const path of paths) {
        const response = await page.goto(base + path, { timeout: 60000 });
        assert.equal(response.status(), 200);
        await page.locator('h1').waitFor();
        await page.waitForLoadState('networkidle');
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, path + ' overflows');
        const audit = await new Axe({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
        accessibility.push({ path, width, violations: audit.violations, incomplete: audit.incomplete.map(x => x.id) });
        assert.equal(audit.violations.length, 0, JSON.stringify(audit.violations.map(x => ({ id: x.id, impact: x.impact }))));
        await page.keyboard.press('Tab');
        assert.equal(await page.evaluate(() => !!document.activeElement && document.activeElement !== document.body), true, 'Keyboard focus unavailable');
        if (path === '/register') {
          await page.getByText('Public registration is currently closed. Contact support for access.', { exact: true }).waitFor();
          assert.equal(await page.locator('#registration-email').count(), 0);
        }
        results.push({ feature: 'Hosted page, overflow, keyboard focus and axe', path, width, status: 'PASS' });
      }
    }
    await page.goto(base + '/app');
    await page.waitForURL('**/login');
    results.push({ feature: 'Anonymous workspace redirects to sign-in', status: 'PASS' });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    assert.equal(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), true);
    assert.equal(await page.evaluate(() => document.getAnimations().filter(a => a.playState === 'running').length), 0);
    results.push({ feature: 'Reduced-motion sign-in page', status: 'PASS' });
    assert.equal(errors.length, 0, errors.join('; '));
    results.push({ feature: 'Hosted JavaScript runtime', status: 'PASS' });
  } catch (e) {
    results.push({ feature: 'Hosted browser acceptance', status: /Timeout|ERR_|net::/.test(e.message) ? 'BLOCKED' : 'FAIL', evidence: e.message.slice(0, 1000) });
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
    fs.writeFileSync(out + '/results.json', JSON.stringify({ base, executed_at: new Date().toISOString(), scope: 'Real hosted anonymous pages; no authentication, email delivery, private repository, or workspace claims', results, accessibility, errors }, null, 2));
    console.log(JSON.stringify({ checks: results.length, passed: results.filter(x => x.status === 'PASS').length, failed: results.filter(x => x.status === 'FAIL').length, blocked: results.filter(x => x.status === 'BLOCKED').length }));
  }
}
main();
