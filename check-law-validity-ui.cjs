const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const report=JSON.parse(fs.readFileSync(path.join(__dirname,'data/validity-all-report.json'),'utf8')),counts=report.counts;
  const page=await browser.newPage({baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1000}}),errors=[];let posts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  await page.goto('/');await page.waitForFunction(()=>document.querySelector('#embedding-profile')?.innerText.includes('索引就绪'));
  await page.click('#corpus');await page.waitForFunction(()=>document.querySelector('#library-summary')?.innerText.includes('本次匹配'));
  await page.selectOption('#library-validity','repealed');await page.waitForFunction(n=>document.querySelector('#library-summary')?.innerText.includes('本次匹配 '+n+' 条'),counts.repealed);
  assert.equal(await page.locator('.validity-status.repealed').count(),20);
  await page.locator('.validity-block summary').first().click();assert.ok((await page.locator('.validity-block a').first().getAttribute('href')).startsWith('https://'));
  await page.selectOption('#library-validity','superseded');await page.waitForFunction(n=>document.querySelector('#library-summary')?.innerText.includes('本次匹配 '+n+' 条'),counts.superseded);
  assert.equal(await page.locator('.validity-status.superseded').count(),20);
  await page.locator('.validity-block summary').first().click();assert.match(await page.locator('.validity-block').first().innerText(),/修改/);
  await page.screenshot({path:path.join(__dirname,'validity-all-desktop.png'),fullPage:true});
  await page.selectOption('#library-validity','partially_repealed');await page.waitForFunction(n=>document.querySelector('#library-summary')?.innerText.includes('本次匹配 '+n+' 条'),counts.partially_repealed);
  await page.locator('.validity-block summary').first().click();assert.match(await page.locator('.validity-block').first().innerText(),/仅本条第一款/);
  await page.selectOption('#library-validity','needs_review');await page.waitForFunction(()=>document.querySelector('.validity-status.needs_review'));
  assert.equal(await page.locator('.validity-status.repealed').count(),0);
  const future=await(await page.request.get('/api/corpus?type=law&validity=not_yet_effective')).json();assert.equal(future.total,465);
  const invalid=await page.request.get('/api/corpus?type=law&validity=invalid');assert.equal(invalid.status(),400);
  const health=await(await page.request.get('/api/health')).json();assert.equal(health.vectors.ready,true);
  assert.deepEqual(errors,[]);assert.equal(posts,0);
  fs.writeFileSync(path.join(__dirname,'data/validity-all-ui-validation.json'),JSON.stringify({passed:true,counts,vectors_ready:true,errors,posts},null,2)+'\n','utf8');
  console.log('PASS: validity badges, filters, provenance, clause scope, pending distinction; vectors ready; no research POST');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
