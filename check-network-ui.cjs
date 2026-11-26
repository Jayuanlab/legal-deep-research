const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const id='fa94d60a3eb64055adf4f67ae8df339a';
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];let posts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  await page.goto('http://127.0.0.1:8765/#job='+id);
  await page.waitForFunction(()=>!document.querySelector('#download').disabled);
  const mode=await page.evaluate(()=>result.retrieval_mode);assert.equal(mode,'hybrid');
  assert.equal(await page.locator('#error').innerText(),'');
  assert.ok(await page.locator('.citation').count()>0);
  await page.screenshot({path:path.join(__dirname,'network-recovery-desktop.png'),fullPage:true});
  // UI-only fault fixture, distinct from the real completed run; no job submission.
  const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'runs',id+'.json'),'utf8'));
  const fake='f'.repeat(32);fixture.id=fake;
  fixture.result.retrieval_mode='bm25_fallback';fixture.result.retrieval_warning='UI fixture: TLS failed';
  fixture.result.report='## 检索降级提示\n\n向量服务暂不可用，后续查询改用本地 BM25。\n\n'+fixture.result.report;
  await page.route('**/api/research/jobs/'+fake,r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fixture)}));
  await page.goto('http://127.0.0.1:8765/#job='+fake);
  await page.waitForFunction(()=>result?.retrieval_mode==='bm25_fallback'&&!document.querySelector('#download').disabled);
  assert.match(await page.locator('#status').innerText(),/BM25降级/);
  assert.match(await page.locator('#report').innerText(),/检索降级提示/);
  await page.screenshot({path:path.join(__dirname,'network-fallback-ui-fixture.png'),fullPage:true});
  assert.equal(posts,0);assert.deepEqual(errors,[]);
  console.log('PASS: real hybrid recovery replay; separately simulated fallback banner/status; no paid task submission');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
