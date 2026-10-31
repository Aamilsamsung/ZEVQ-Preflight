/* Fixed-target external probe. No source, organization identities or secret details in alerts. */
'use strict';
const BASE='https://zevq-preflight-staging.onrender.com';
async function probe(fetcher=fetch,token=process.env.PREFLIGHT_MONITOR_TOKEN){
 for(const path of ['/health',...(token?['/api/operations/monitor']:[])]){
  try{const r=await fetcher(BASE+path,{headers:path.includes('/operations/')?{Authorization:'Bearer '+token}:{},signal:AbortSignal.timeout(5000),redirect:'error'});
   if(!r.ok)return false;const body=await r.json();if(body.status!=='ok')return false;
  }catch{return false}
 }
 return true;
}
async function run(github,context,{probeFn=probe,pause=ms=>new Promise(r=>setTimeout(r,ms))}={}){
 if(process.env.PREFLIGHT_MONITOR_ENABLED!=='true'){console.log('External monitoring disabled: owner must enable the repository variable.');return}
 const title='ZEVQ staging operational monitor incident';const repo=context.repo;
 const issues=await github.rest.issues.listForRepo({...repo,state:'open',creator:'github-actions[bot]',per_page:100});
 const existing=issues.data.find(i=>i.title===title&&!i.pull_request);
 let healthy=false;for(let i=0;i<3;i++){healthy=await probeFn();if(healthy)break;if(i<2)await pause(10000)}
 if(!healthy&&!existing){await github.rest.issues.create({...repo,title,body:'Three consecutive fixed-target probes failed. Inspect the private Render service logs and health configuration. No source, credentials, tenant details or provider error bodies are included. This issue is an external alert record; inbox receipt must be verified separately.'})}
 else if(healthy&&existing){await github.rest.issues.createComment({...repo,issue_number:existing.number,body:'Recovery observed: the fixed health and configured operational probes returned healthy. This does not prove every application workflow is functional.'});await github.rest.issues.update({...repo,issue_number:existing.number,state:'closed'})}
 console.log(JSON.stringify({status:healthy?'healthy':'incident',operations_probe:!!process.env.PREFLIGHT_MONITOR_TOKEN}));
}
module.exports={probe,run};
