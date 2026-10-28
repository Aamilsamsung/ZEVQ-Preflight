/* Supplemental local checks reproduce the audited commit's UI defects. */
const fs=require('fs');const {spawn}=require('child_process');const {chromium}=require('playwright');const assert=require('assert/strict');
(async()=>{const results=[],axe=[];const children=[];const output=process.env.QA_AUDIT_OUTPUT||'artifacts/independent-audit';fs.mkdirSync(output,{recursive:true});const record=async(name,fn)=>{try{await fn();results.push({feature:name,status:'PASS'})}catch(e){results.push({feature:name,status:'FAIL',evidence:e.message})}};
let launch={headless:true};if(process.env.QA_CHROMIUM_MODULE){const binary=(await import(process.env.QA_CHROMIUM_MODULE)).default;launch={...launch,executablePath:await binary.executablePath(),args:binary.args.filter(a=>a!=='--disable-web-security'&&a!=='--single-process'&&!a.startsWith('--ignore-certificate-errors'))}}
const python=process.env.QA_PYTHON||(fs.existsSync('.venv/bin/python')?'.venv/bin/python':'python');
children.push(spawn(python,['-m','uvicorn','app.main:app','--port','8011'],{stdio:'ignore'}));
let browser;try{for(let i=0;i<60;i++){try{if((await fetch('http://127.0.0.1:8011/health')).ok)break}catch{}await new Promise(r=>setTimeout(r,200))}
browser=await chromium.launch(launch);const context=await browser.newContext({viewport:{width:1440,height:1000}});const page=await context.newPage();const AxeBuilder=require(process.env.QA_AXE_MODULE||'@axe-core/playwright').default;
for(const path of ['/','/login']){await page.goto('http://127.0.0.1:8011'+path);await page.locator('h1').waitFor();axe.push({page:path,...await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()})}
const creds=JSON.parse(fs.readFileSync('artifacts/qa-credentials.json'));await page.locator('#email').fill(creds.email);await page.locator('#password').fill(creds.password);await page.getByRole('button',{name:'Sign in to workspace'}).click();await page.waitForURL('**/app');await record('Signed-in landing CTA opens workspace',async()=>{await page.goto('http://127.0.0.1:8011/');await page.getByRole('link',{name:'Open your workspace',exact:false}).click();await page.waitForURL('**/app');await page.getByRole('heading',{name:'Deployment overview'}).waitFor()});
await record('Owner role editor persists membership changes',async()=>{
 await page.goto('http://127.0.0.1:8011/app#team');await page.getByRole('heading',{name:'Team members',exact:true}).waitFor();
 const editor=page.getByRole('combobox',{name:'Role for qa-viewer@example.test',exact:true});
 for(const role of ['developer','viewer']){
  await editor.selectOption(role);await page.getByRole('row').filter({hasText:'qa-viewer@example.test'}).getByRole('button',{name:'Update role',exact:true}).click();
  await page.getByRole('dialog',{name:'Change member role?',exact:true}).waitFor();
  await Promise.all([page.waitForResponse(r=>r.request().method()==='PATCH'&&r.url().includes('/members/')&&r.status()===200),page.getByRole('button',{name:'Confirm',exact:true}).click()]);
  await page.reload();await page.getByRole('heading',{name:'Team members',exact:true}).waitFor();assert.equal(await editor.inputValue(),role)
 }
});
await record('Password confirmation mismatch is actionable',async()=>{
 await page.goto('http://127.0.0.1:8011/app#settings');await page.getByRole('heading',{name:'Password and session security',exact:true}).waitFor();
 await page.locator('#current-password').fill(creds.password);await page.locator('#new-password').fill('synthetic-test-password-one');await page.locator('#confirm-password').fill('synthetic-test-password-two');await page.getByRole('button',{name:'Change password',exact:true}).click();await page.getByText('New passwords do not match.',{exact:true}).waitFor();
 assert.equal(await page.locator('#current-password').isVisible(),true)
});
await record('Finding decisions persist, expire explicitly and retain history',async()=>{
 const fixture=JSON.parse(fs.readFileSync('artifacts/qa-review-scan.json'));
 await page.goto('http://127.0.0.1:8011/app#scan/'+fixture.scan_id);
 await page.getByRole('heading',{name:'Analysis report',exact:true}).waitFor();
 const finding=page.locator('.finding').first();const risk=await page.locator('main').innerText();
 for(const [status,reason] of [['acknowledged','Synthetic browser review acknowledged'],['suppressed','Synthetic browser suppression with expiry'],['open','Synthetic browser review reopened']]){
  await finding.locator('.decision-summary').click();await finding.getByLabel('Decision',{exact:true}).selectOption(status);
  await finding.getByLabel('Reason',{exact:true}).fill(reason);
  if(status==='suppressed')assert.ok(await finding.getByLabel('Expiry (your local time)',{exact:true}).inputValue());
  await Promise.all([page.waitForResponse(r=>r.request().method()==='PUT'&&r.url().endsWith('/review')&&r.status()===200),finding.getByRole('button',{name:'Save decision',exact:true}).click()]);
  await finding.locator('.review-reason').filter({hasText:reason}).waitFor();await page.reload();await finding.locator('.review-reason').filter({hasText:reason}).waitFor();
 }
 await finding.locator('.decision-summary').click();await finding.getByRole('button',{name:'Load decision history',exact:true}).click();await finding.getByRole('cell',{name:'Synthetic browser review acknowledged',exact:true}).waitFor();assert.equal(await finding.locator('tbody tr').count(),3);
 assert.match(await page.locator('main').innerText(),/Original|original/);
 axe.push({page:'finding-review',...await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()});
});
await record('Scan comparison selects real reports and preserves uncertainty',async()=>{
 const fixture=JSON.parse(fs.readFileSync('artifacts/qa-comparison.json'));
 await page.goto('http://127.0.0.1:8011/app#history');await page.getByLabel('Earlier report',{exact:true}).selectOption(fixture.baseline_id);await page.getByLabel('Later report',{exact:true}).selectOption(fixture.baseline_id);await page.getByRole('button',{name:'Compare findings',exact:true}).click();await page.getByText('Choose two different scans.',{exact:true}).waitFor();
 await page.getByLabel('Later report',{exact:true}).selectOption(fixture.proposed_id);await page.getByRole('button',{name:'Compare findings',exact:true}).click();await page.getByRole('heading',{name:'Compare scan findings',exact:true}).waitFor();
 await page.getByRole('heading',{name:'No longer observed findings',exact:true}).waitFor();assert.match(await page.locator('main').innerText(),/Not observed does not mean fixed/);
 assert.equal(await page.getByRole('link',{name:'Review in original report',exact:true}).count(),1);
 const download=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Download comparison JSON',exact:true}).click()]);const exported=JSON.parse(fs.readFileSync(await download[0].path()));assert.equal(exported.counts.not_observed,1);assert.equal(exported.counts.added,0);
 await page.reload();await page.getByRole('heading',{name:'Compare scan findings',exact:true}).waitFor();
 for(const width of [390,768,1440]){await page.setViewportSize({width,height:1000});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false)}
 axe.push({page:'scan-comparison',...await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()});
});
await record('Retention policy and dry run do not delete data',async()=>{
 await page.goto('http://127.0.0.1:8011/app#settings');await page.getByLabel('Retention age in days',{exact:true}).fill('7');await page.getByRole('button',{name:'Save retention policy',exact:true}).click();await page.getByRole('button',{name:'Run cleanup dry run',exact:true}).waitFor();
 await page.getByRole('button',{name:'Run cleanup dry run',exact:true}).click();await page.getByText(/Dry run only:/).waitFor();assert.equal(await page.getByRole('button',{name:'Permanently delete previewed scans',exact:true}).count(),0);assert.doesNotMatch(await page.locator('main').innerText(),/\bnull\b/);
 await page.getByRole('button',{name:'Load cleanup history',exact:true}).click();await page.getByRole('cell',{name:'preview',exact:true}).first().waitFor();
 await page.getByLabel('Retention age in days',{exact:true}).fill('');await page.getByRole('button',{name:'Save retention policy',exact:true}).click();await page.reload();await page.getByRole('heading',{name:'Data retention',exact:true}).waitFor();assert.equal(await page.getByRole('button',{name:'Run cleanup dry run',exact:true}).isDisabled(),true)
});
await record('Notifications use stored operational data',async()=>{await page.goto('http://127.0.0.1:8011/app#alerts');await page.getByRole('heading',{name:'Notifications',exact:true}).waitFor();await page.getByText('Email, Slack and external service-availability alerts are not configured.',{exact:true}).waitFor()});
await record('Mobile audit table supports keyboard access',async()=>{
 await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:8011/app#audit');await page.getByRole('heading',{name:'Audit log',exact:true}).waitFor();const region=page.getByRole('region',{name:'Scrollable data table',exact:true}).first();await region.press('ArrowRight');assert.equal(await region.evaluate(n=>n===document.activeElement),true);const a=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();assert.equal(a.violations.some(v=>v.id==='scrollable-region-focusable'),false);axe.push({page:'mobile-audit',...a});await page.setViewportSize({width:1440,height:1000})
});
for(const path of ['/app#dashboard','/app#settings','/app#new']){await page.goto('http://127.0.0.1:8011'+path);await page.locator('main h1').waitFor();axe.push({page:path,...await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()})}
await page.getByRole('tab',{name:'API / OpenAPI'}).click();const doc=JSON.stringify({openapi:'3.0.3',paths:{}});await page.locator('#baseline-contract').fill(doc);await page.locator('#proposed-contract').fill(doc);await page.getByRole('button',{name:'Continue to Configuration'}).click();await page.getByRole('button',{name:'Continue to Review'}).click();await record('Review renders four real summary rows',async()=>{assert.equal(await page.locator('.wizard-review .key-value').count(),4);assert.doesNotMatch(await page.locator('.wizard-review').innerText(),/\[object HTMLDivElement\]/)});
await page.goto('http://127.0.0.1:8011/app#settings');await page.getByRole('button',{name:'Delete account',exact:true}).click();await record('Confirmation dialog has accessible name',async()=>{await page.getByRole('dialog',{name:'Permanently delete your account?',exact:true}).waitFor({timeout:1000})});axe.push({page:'confirmation-dialog',...await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()});await page.getByRole('button',{name:'Cancel',exact:true}).click();
for(const a of axe)results.push({feature:'Accessibility '+a.page,status:a.violations.length?'FAIL':'PASS',evidence:a.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.length,description:v.description}))});
}finally{if(browser)await browser.close();children.forEach(c=>c.kill());fs.writeFileSync(output+'/frontend-results.json',JSON.stringify({results,axe:axe.map(a=>({page:a.page,violations:a.violations,incomplete:a.incomplete.map(i=>i.id)}))},null,2));console.log(JSON.stringify({checks:results.length,passed:results.filter(r=>r.status==='PASS').length,failed:results.filter(r=>r.status==='FAIL')},null,2));if(results.some(r=>r.status==='FAIL'))process.exitCode=1}})().catch(e=>{console.error(e.message);process.exitCode=1});
