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
  const summary=await page.evaluate(()=>({outcome:result.outcome,rounds:result.supplement_rounds,accepted:result.verification.accepted,article9:result.evidence.some(d=>d.id==='E26009'),invalid:result.verification.invalid}));
  assert.ok(summary.article9);assert.deepEqual(summary.invalid,[]);
  const cite=page.locator('.citation[data-ref="E26009"]');if(await cite.count())await cite.first().click();
  await page.screenshot({path:require('node:path').join(__dirname,'guarantee-report-desktop.png'),fullPage:true});
  await page.locator('[data-proof="verification"]').click();
  assert.ok(await page.locator('.claim-check').count()>0);
  await page.screenshot({path:require('node:path').join(__dirname,'guarantee-verification-desktop.png'),fullPage:true});
  assert.equal(submissions,0);assert.deepEqual(errors,[]);
  console.log('PASS: real guarantee run replay, article9 evidence, citations, validation UI, no duplicate submissions '+JSON.stringify(summary));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
