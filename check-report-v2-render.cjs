const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});try{
 const page=await browser.newPage({baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1000}});let posts=0;const errors=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
 await page.goto('/');await page.waitForFunction(()=>document.querySelector('#embedding-profile')?.innerText.includes('索引就绪'));
 const health=await(await page.request.get('/api/health')).json();assert.equal(health.report_version,'legal-report-v2');
 await page.evaluate(()=>{document.querySelector('#report').innerHTML=renderReport('# 报告标题\n\n#### 事实适用\n\n- 题设陈述\n\n支持依据 [J123A2_0]\n\n[官方来源](https://www.court.gov.cn/)\n\n<img src=x onerror="window.__reportXss=1">\n\n[恶意链接](javascript:alert(1))');document.querySelector('#evidence').innerHTML='<section id="J123A2_0">证据定位</section>'});
 assert.equal(await page.locator('#report h1').count(),1);assert.equal(await page.locator('#report h4').count(),1);assert.equal(await page.locator('#report li').count(),1);
 assert.equal(await page.locator('#report img').count(),0);assert.equal(await page.locator('#report a').count(),1);assert.equal(await page.locator('#report .citation').getAttribute('data-ref'),'J123A2_0');
 assert.equal(await page.evaluate(()=>window.__reportXss),undefined);await page.locator('#report .citation').click();
 assert.equal(posts,0);assert.deepEqual(errors,[]);console.log('PASS: report headings, lists, generic citation navigation, safe links and HTML escaping; zero research POST');
 fs.writeFileSync(path.join(__dirname,'runs/report-v2/render-validation.json'),JSON.stringify({passed:true,page_errors:errors,research_posts:posts,html_escaped:true,generic_source_links:true},null,2)+'\n','utf8');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
