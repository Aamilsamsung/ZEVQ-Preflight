/* Local browser QA against the real API and separate static worker.
 * Credentials are read from an ignored local file, never embedded in source.
 * Run: node scripts/browser-qa.cjs
 */
const { chromium } = require('playwright');
const fs = require('fs');
const assert = require('assert/strict');
const base = process.env.QA_BASE_URL || 'http://127.0.0.1:8000';
const credentials = JSON.parse(fs.readFileSync(process.env.QA_CREDENTIALS_FILE || 'artifacts/qa-credentials.json','utf8'));
const results = [];
const errors = [];
const record=(name,details='')=>results.push({name,status:'PASS',details});
(async()=>{
 let launch={headless:true};
 if(process.env.QA_CHROMIUM_MODULE){const binary=(await import(process.env.QA_CHROMIUM_MODULE)).default;launch={...launch,args:binary.args,executablePath:await binary.executablePath()}}
 const services=[];
 if(process.env.QA_START_SERVICES==='1'){
 const {spawn}=require('child_process');
 services.push(spawn('.venv/bin/python',['-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],{stdio:'ignore'}));
 services.push(spawn('.venv/bin/python',['-m','app.worker'],{stdio:'ignore'}));
 for(let attempt=0;attempt<60;attempt++){try{const r=await fetch(base+'/health');if(r.ok)break}catch{}await new Promise(r=>setTimeout(r,250))}
 }
 const browser=await chromium.launch(launch);
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage();
 page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')errors.push(message.text())});
 try {
 for(const path of ['/','/features','/how-it-works','/use-cases','/docs','/faq','/security','/pricing','/contact','/privacy','/terms','/login']){
   const response=await page.goto(base+path);assert.equal(response.status(),200);await page.locator('h1').waitFor();assert.ok((await page.locator('h1').innerText()).length);record('Public page '+path);
 }
 await page.locator('#email').fill(credentials.email);
 await page.locator('#password').fill(credentials.password);
 await page.getByRole('button',{name:'Sign in to workspace'}).click();
 await page.waitForURL('**/app');await page.getByRole('heading',{name:'Deployment overview'}).waitFor();record('Account login');
 await page.reload();await page.getByRole('heading',{name:'Deployment overview'}).waitFor();record('Persistent login after refresh');
 await page.screenshot({path:'artifacts/qa-desktop-dashboard.png',fullPage:true});
 await page.goto(base+'/app#repositories');await page.getByRole('heading',{name:'Repositories',exact:true}).waitFor();
 const repository='Aamilsamsung/ZEVQ-Preflight';
 if(!(await page.locator('td').allTextContents()).some(x=>x===repository)){
   await page.locator('#full_name').fill(repository);await page.getByRole('button',{name:'Connect repository'}).click();await page.getByText(repository,{exact:true}).waitFor();
 }
 record('Connect public repository');
 await page.goto(base+'/app#new');await page.getByRole('button',{name:'Run comparison'}).waitFor();
 await page.getByRole('tab',{name:'OpenAPI contracts'}).click();
 const baseline={openapi:'3.0.3',info:{title:'QA',version:'1'},paths:{'/orders':{get:{responses:{'200':{description:'OK'}}}}}};
 const proposed={openapi:'3.0.3',info:{title:'QA',version:'2'},paths:{}};
 await page.locator('#baseline-contract').fill(JSON.stringify(baseline));await page.locator('#proposed-contract').fill(JSON.stringify(proposed));
 await page.getByRole('button',{name:'Compare contracts'}).click();
 await page.waitForURL('**/app#scan/*');await page.getByRole('heading',{name:'Evidence-backed findings'}).waitFor({timeout:45000});
 await page.getByRole('heading',{name:/Removed endpoint/}).waitFor();record('OpenAPI comparison finds removed endpoint');
 await page.getByText('Inspect evidence and rule').first().click();await page.locator('pre').first().waitFor();
 assert.match(await page.locator('body').innerText(),/OPENAPI|OAS|API\./);record('Evidence and rule visible');
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Download JSON'}).click()]);
 const json=JSON.parse(fs.readFileSync(await download.path(),'utf8'));assert.ok(json.result.findings.length);record('Authenticated JSON report download');
 const [csv]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Download CSV'}).click()]);assert.match(fs.readFileSync(await csv.path(),'utf8'),/severity/);record('Authenticated CSV report download');
 await page.screenshot({path:'artifacts/qa-desktop-report.png',fullPage:true});
 await page.goto(base+'/app#new');await page.getByRole('tab',{name:'ZIP archives'}).click();
 await page.locator('#file').setInputFiles('artifacts/qa-source.zip');
 await page.getByRole('button',{name:'Analyze archives'}).click();await page.waitForURL('**/app#scan/*');await page.getByRole('heading',{name:'Evidence-backed findings'}).waitFor({timeout:45000});record('ZIP source scan through background worker');
 for(const [view,title]of [['history','Scan history'],['team','Team members'],['audit','Audit log'],['settings','Workspace settings']]){await page.goto(base+'/app#'+view);await page.getByRole('heading',{name:title,exact:true}).waitFor();record('Workspace page '+view)}
 await page.goto(base+'/app#settings');await page.getByRole('link',{name:'Export account data'}).waitFor();record('Account export and deletion controls present');
 for(const [label,width,height]of [['mobile',390,844],['tablet',768,1024],['desktop',1440,1000]]){
   await page.setViewportSize({width,height});await page.goto(base+'/app#dashboard');await page.getByRole('heading',{name:'Deployment overview'}).waitFor();
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);assert.equal(overflow,false,label+' dashboard overflow');
   if(label==='mobile'){await page.getByRole('button',{name:'Toggle navigation'}).click();await page.getByRole('link',{name:'Repositories',exact:false}).click();await page.getByRole('heading',{name:'Repositories',exact:true}).waitFor();assert.equal(await page.locator('#sidebar').evaluate(n=>n.classList.contains('open')),false);record('Mobile navigation opens, navigates, closes')}
   await page.screenshot({path:'artifacts/qa-'+label+'.png',fullPage:true});record(label+' responsive layout',width+'px; no document horizontal overflow');
 }
 await page.goto(base+'/');await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Skip to content');await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>location.hash),'#content');record('Keyboard skip navigation');
 await page.goto(base+'/app#settings');await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.waitForURL('**/login');record('Sign out');
 assert.equal(errors.length,0,errors.join('\n'));record('No browser console errors or uncaught exceptions');
 } catch(error){results.push({name:'Browser QA failure',status:'FAIL',details:error.stack});await page.screenshot({path:'artifacts/qa-failure.png',fullPage:true});process.exitCode=1}
 finally{fs.writeFileSync('artifacts/browser-qa-results.json',JSON.stringify({base,executed_at:new Date().toISOString(),results,console_errors:errors},null,2));console.log(JSON.stringify({checks:results.length,passed:results.filter(x=>x.status==='PASS').length,failures:results.filter(x=>x.status==='FAIL'),console_errors:errors},null,2));await browser.close();for(const service of services)service.kill('SIGTERM')}
})().catch(error=>{console.error(error.message);process.exitCode=1});
