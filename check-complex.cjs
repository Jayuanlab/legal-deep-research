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
  const summary=await page.evaluate(()=>({outcome:result.outcome,issues:result.research_plan.issues.length,rounds:result.supplement_rounds,evidence:result.evidence.length,accepted:result.verification.accepted,invalid:result.verification.invalid}));
  assert.equal(summary.issues,4);assert.ok(summary.rounds>=1);assert.ok(summary.evidence>0);assert.ok(summary.accepted>0);assert.deepEqual(summary.invalid,[]);
  await page.locator('.citation').first().click();
  assert.equal(await page.locator('#evidence .evidence-item').count(),summary.evidence);
  await page.screenshot({path:require('node:path').join(__dirname,'complex-report-desktop.png'),fullPage:true});
  await page.locator('[data-tab="trace"]').click();
  assert.match(await page.locator('#trace').innerText(),/补充检索/);
  await page.screenshot({path:require('node:path').join(__dirname,'complex-trace-desktop.png'),fullPage:true});
  assert.equal(submissions,0);assert.deepEqual(errors,[]);
  console.log('PASS: linked real run, four issues, new supplemental evidence, citations and desktop trace '+JSON.stringify(summary));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
