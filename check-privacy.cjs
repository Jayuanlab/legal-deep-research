const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const id=process.env.LEGAL_JOB_ID;assert.match(id,/^[a-f0-9]{32}$/);
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];let submissions=0;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/research/jobs'))submissions++});
  await page.goto('http://127.0.0.1:8765/#job='+id);
  await page.waitForFunction(()=>!document.querySelector('#download').disabled||document.querySelector('#error').textContent,{},{timeout:600000});
  assert.equal(await page.locator('#error').innerText(),'');
  const summary=await page.evaluate(()=>({outcome:result.outcome,elapsed:result.elapsed,accepted:result.verification.accepted,invalid:result.verification.invalid,facts:result.verification.checks.map(c=>({id:c.claim_id,status:c.status,fact:c.fact_status,reason:c.fact_reason}))}));
  assert.deepEqual(summary.invalid,[]);
  assert.ok(summary.facts.length>0);
  for(const row of summary.facts)if(row.status==='supported')assert.ok(['grounded','conditional'].includes(row.fact));
  await page.screenshot({path:require('node:path').join(__dirname,'privacy-report-desktop.png'),fullPage:true});
  await page.locator('[data-proof="verification"]').click();
  assert.match(await page.locator('#verification').innerText(),/事实前提/);
  await page.screenshot({path:require('node:path').join(__dirname,'privacy-verification-desktop.png'),fullPage:true});
  assert.equal(submissions,0);assert.deepEqual(errors,[]);
  console.log('PASS: real privacy run replay, separate fact checks, desktop validation, no duplicate submission '+JSON.stringify(summary));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
