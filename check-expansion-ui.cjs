const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];let posts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(()=>document.querySelector('.scope p')?.textContent.includes('2782'));
  assert.match(await page.locator('.scope p').innerText(),/319/);
  const health=await(await page.request.get('http://127.0.0.1:8765/api/health')).json();
  assert.equal(health.vectors.ready,true);assert.equal(health.vectors.chunks,3421);
  assert.equal(health.models.embedding_model,'text-embedding-v4');
  await page.click('#corpus');await page.selectOption('#library-type','case');
  await page.fill('#library-query','过度收集');await page.click('#library-form button');
  await page.locator('#library-T20305').waitFor();
  assert.match(await page.locator('#library-T20305').innerText(),/非指导案例/);
  await page.screenshot({path:path.join(__dirname,'expanded-cases-desktop.png'),fullPage:true});
  await page.selectOption('#library-type','law');
  await page.fill('#library-query','领取退休金');await page.click('#library-form button');
  await page.locator('#library-E27032').waitFor();
  assert.match(await page.locator('#library-E27032').innerText(),/第一款.*废止/);
  assert.match(await page.locator('#library-E27032 .withdrawn').innerText(),/涉及废止/);
  assert.equal(posts,0);assert.deepEqual(errors,[]);
  console.log('PASS: expanded counts, ready Aliyun index, typical-case label, partial-repeal warning; no research submission');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
