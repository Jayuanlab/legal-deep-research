const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1000}}),errors=[];
  let posts=0;page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  const expected=JSON.parse(fs.readFileSync(path.join(__dirname,'data/gap185-import-manifest.json'),'utf8')).after;
  await page.goto('http://127.0.0.1:8765/');
  await page.waitForFunction(n=>document.querySelector('.scope p')?.textContent.includes(String(n)),expected.laws);
  const h=await(await page.request.get('/api/health')).json();assert.equal(h.laws,expected.laws);assert.equal(h.vectors.ready,true);assert.equal(h.models.embedding_model,'text-embedding-v4');
  const c=await(await page.request.get('/api/catalog')).json();assert.equal(c.coverage.title_matches,303);assert.equal(c.coverage.missing_titles,0);assert.equal(c.coverage.all_china_complete,false);
  await page.click('#corpus');await page.locator('#library-coverage').waitFor();assert.match(await page.locator('#library-coverage').innerText(),/303/);
  await page.selectOption('#library-topic','全国性法律');await page.fill('#library-query','自愿加入或取得外国国籍');await page.click('#library-form button');
  await page.waitForFunction(()=>document.querySelector('#library-content')?.innerText.includes('国籍法'));
  await page.screenshot({path:path.join(__dirname,'gap185-laws-desktop.png'),fullPage:true});
  await Promise.all([page.waitForResponse(r=>r.url().includes('/api/corpus?')&&r.url().includes('type=case')),page.selectOption('#library-type','case')]);
  await page.waitForFunction(()=>!document.querySelector('#library-summary').textContent.includes('加载中'));
  await page.fill('#library-query','百度');await page.click('#library-form button');
  await page.waitForFunction(()=>document.querySelector('#library-content')?.innerText.includes('百度'));
  // Verify the retained case library separately from the law topic filter.
  const cases=await(await page.request.get('/api/corpus?type=case&q='+encodeURIComponent('百度'))).json();
  assert.ok(JSON.stringify(cases).includes('百度'));assert.equal(posts,0);assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'data/gap185-ui-validation.json'),JSON.stringify({passed:true,counts:expected,title_matches:303,missing_titles:0,vectors_ready:h.vectors.ready,research_posts:posts,page_errors:errors},null,2)+'\n','utf8');
  console.log('PASS: desktop corpus, 303-title scope, ready Aliyun index, new law search, retained case library; zero research POST');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
