const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];let posts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(()=>document.querySelector('#embedding-profile')?.textContent.includes('text-embedding-v4'));
  assert.match(await page.locator('#embedding-profile').innerText(),/1024维.*索引就绪/);
  const health=await (await page.request.get('http://127.0.0.1:8765/api/health')).json();
  assert.equal(health.models.embedding_model,'text-embedding-v4');assert.equal(health.models.text_model,'qwen3.7-plus');
  assert.equal(health.vectors.ready,true);assert.equal(health.vectors.indexed_chunks,3421);
  await page.screenshot({path:path.join(__dirname,'aliyun-desktop.png'),fullPage:true});
  assert.equal(posts,0);assert.deepEqual(errors,[]);
  console.log('PASS: active Aliyun model, 1024 dimensions, 3421 ready chunks, desktop model label; no research submission');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
