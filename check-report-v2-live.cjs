const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{const root=path.join(__dirname,'runs/report-v2'),job=JSON.parse(fs.readFileSync(path.join(root,'candidate-job.json'),'utf8'));assert.equal(job.status,'completed');
 const browser=await chromium.launch({channel:'msedge',headless:true});try{
  const page=await browser.newPage({baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1080},acceptDownloads:true}),errors=[];let posts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST')posts++});
  await page.goto('/#job='+job.id);await page.locator('#report h1').waitFor({timeout:30000});
  const text=await page.locator('#report').innerText();for(const title of ['结论摘要','事实与材料基础','逐争点分析','事实与要件适用','支持理由','可能抗辩与回应','类案比较','行动建议','规范与案例依据'])assert.ok(text.includes(title),title);
  assert.equal(await page.locator('#report h1').innerText(),'专项法律研究报告');assert.ok(await page.locator('#report .citation').count()>5);
  assert.ok(await page.locator('#report a').count()>0);await page.screenshot({path:path.join(root,'candidate-desktop.png'),fullPage:false});
  await page.locator('#report h2').filter({hasText:'四、类案比较'}).evaluate(n=>n.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(root,'candidate-cases.png'),fullPage:false});
  await page.locator('#report h2').filter({hasText:'五、行动建议'}).evaluate(n=>n.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(root,'candidate-actions.png'),fullPage:false});
  const citation=page.locator('#report .citation').first(),ref=await citation.getAttribute('data-ref');await citation.click();assert.ok(await page.locator('[id="'+ref+'"]').isVisible());
  const downloadPromise=page.waitForEvent('download');await page.click('#download');const download=await downloadPromise;const exportPath=path.join(root,'candidate-export.md');await download.saveAs(exportPath);
  const exported=fs.readFileSync(exportPath,'utf8');assert.ok(exported.includes(job.result.report));assert.ok(exported.includes('事实与要件适用'));assert.ok(!exported.includes('\uFFFD'));
  assert.deepEqual(errors,[]);assert.equal(posts,0);
  fs.writeFileSync(path.join(root,'live-ui-validation.json'),JSON.stringify({passed:true,job_id:job.id,headings:true,citation_navigation:true,complete_export:true,page_errors:errors,new_research_posts:posts},null,2)+'\n','utf8');
  console.log('PASS: actual report, complete sections, source navigation and full export; existing job restored; zero new research POST');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
