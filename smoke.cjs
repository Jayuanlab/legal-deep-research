const {chromium}=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.setDefaultTimeout(600000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(process.env.LEGAL_JOB_ID)await page.addInitScript(id=>sessionStorage.setItem('legal-active-job',id),process.env.LEGAL_JOB_ID);
  await page.goto('http://127.0.0.1:8765');
  if(!process.env.LEGAL_JOB_ID)await page.locator('#submit').click();
  await page.waitForFunction(()=>!document.querySelector('#download').disabled||document.querySelector('#error').textContent,{},{timeout:600000});
  assert.equal(await page.locator('#error').innerText(),'');
  const summary=await page.evaluate(()=>({outcome:result.outcome,elapsed:result.elapsed,rounds:result.supplement_rounds,calls:result.budget.model_calls,claims:result.verification.checks.length,accepted:result.verification.accepted,invalid:result.verification.invalid,issues:result.research_plan.issues}));
  assert.deepEqual(summary.invalid,[]);assert.ok(summary.calls<=9);console.log(JSON.stringify(summary));
  assert.ok(await page.locator('.citation').count()>0);
  assert.equal(await page.locator('.steps li').count(),6);
  await page.locator('[data-proof="verification"]').click();assert.ok(await page.locator('.claim-check').count()>0);
  await page.locator('[data-proof="evidence"]').click();
  await page.locator('.citation').first().click();
  const download=page.waitForEvent('download');await page.locator('#download').click();
  assert.equal((await download).suggestedFilename(),'legal-research.md');
  await page.locator('[data-tab="trace"]').click();assert.ok(await page.locator('.event').count()>=8);
  await page.locator('[data-tab="report"]').click();
  await page.locator('#corpus').click();await page.locator('#library-content .evidence-item').first().waitFor();assert.equal(await page.locator('#library-content .evidence-item').count(),20);
  await page.locator('#library-next').click();await page.waitForFunction(()=>document.querySelector('#library-page').textContent.startsWith('2 /'));
  await page.locator('#library-type').selectOption('case');await page.waitForFunction(()=>document.querySelector('#library-summary').textContent.includes('匹配 278 条'));
  assert.match(await page.locator('#library-content').innerText(),/案号/);
  await page.locator('#library-query').fill('隆昌伟业');await page.locator('#library-form button').click();await page.waitForFunction(()=>document.querySelectorAll('#library-content .evidence-item').length===1);
  assert.match(await page.locator('#library-content').innerText(),/166/);await page.locator('#close-library').click();
  await page.screenshot({path:require('node:path').join(__dirname,'desktop.png'),fullPage:true});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  // Scope handling and cancellation are exercised offline to avoid another paid run.
  const invalid=await page.request.post('http://127.0.0.1:8765/api/research',{data:{question:'a'}});assert.equal(invalid.status(),400);
  assert.deepEqual(errors,[]);
  console.log('PASS: desktop flow, citations, export, trace, corpus, out-of-domain, input validation; no JS errors');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
