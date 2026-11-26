const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const expected=JSON.parse(fs.readFileSync(path.join(__dirname,'data/bulk-import-manifest.json'),'utf8')).after;
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];let posts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(n=>document.querySelector('.scope p')?.textContent.includes(String(n)),expected.laws);
  const health=await(await page.request.get('http://127.0.0.1:8765/api/health')).json();
  assert.equal(health.laws,expected.laws);assert.equal(health.cases,expected.cases);
  assert.equal(health.vectors.ready,true);assert.equal(health.models.embedding_model,'text-embedding-v4');
  const catalog=await(await page.request.get('http://127.0.0.1:8765/api/catalog')).json();
  assert.equal(catalog.coverage.all_china_complete,false);assert.equal(catalog.coverage.missing_titles,185);
  await page.click('#corpus');await page.locator('#library-coverage').waitFor();
  assert.match(await page.locator('#library-coverage').innerText(),/185/);
  await page.selectOption('#library-topic','全国性法律');await page.fill('#library-query','加处罚款');await page.click('#library-form button');
  await page.waitForFunction(()=>document.querySelector('#library-content')?.innerText.includes('行政强制法'));
  await page.screenshot({path:path.join(__dirname,'bulk-laws-desktop.png'),fullPage:true});
  await page.selectOption('#library-type','case');await page.fill('#library-query','百度 奥商');await page.click('#library-form button');
  await page.locator('#library-C1045').waitFor();
  assert.match(await page.locator('#library-C1045').innerText(),/转载/);
  assert.equal(posts,0);assert.deepEqual(errors,[]);
  console.log('PASS: live expanded corpus, ready Aliyun index, explicit coverage gaps, recovered guide provenance; no research POST');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
