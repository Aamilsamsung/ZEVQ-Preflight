const assert=require('node:assert/strict');const {probe,run}=require('./external_monitor.cjs');
(async()=>{
assert.equal(await probe(async()=>({ok:true,json:async()=>({status:'ok'})}),'fixture-token'),true);
assert.equal(await probe(async()=>({ok:false}),''),false);
assert.equal(await probe(async()=>{throw Error('private-secret')},''),false);
assert.equal(await probe(async()=>({ok:true,json:async()=>({status:'degraded'})}),'fixture-token'),false);
let urls=[];await probe(async(u,o)=>{urls.push(u);assert.equal(o.redirect,'error');return {ok:true,json:async()=>({status:'ok'})}},'fixture-token');assert.equal(urls.length,2);assert(urls.every(u=>u.startsWith('https://zevq-preflight-staging.onrender.com/')));
let existing=[],created=0,recovered=0,closed=0,probes=0;const github={rest:{issues:{listForRepo:async()=>({data:existing}),create:async p=>{created++;existing=[{title:p.title,number:1}]},createComment:async()=>{recovered++},update:async()=>{closed++;existing=[]}}}};
process.env.PREFLIGHT_MONITOR_ENABLED='true';const incident={probeFn:async()=>{probes++;return false},pause:async()=>{}};
await run(github,{repo:{owner:'fixture',repo:'fixture'}},incident);assert.equal(created,1);assert.equal(probes,3);
await run(github,{repo:{owner:'fixture',repo:'fixture'}},incident);assert.equal(created,1);
await run(github,{repo:{owner:'fixture',repo:'fixture'}},{probeFn:async()=>true});assert.equal(recovered,1);assert.equal(closed,1);
console.log('External monitor: 8 deterministic checks passed; real notification delivery NOT TESTED.');
})().catch(e=>{console.error(e);process.exitCode=1});
