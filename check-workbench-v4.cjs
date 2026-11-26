const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const root=path.join(__dirname,'runs/workbench-v4');const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({baseURL:'http://127.0.0.1:8765',viewport:{width:1440,height:1080},acceptDownloads:true});const errors=[];let researchPosts=0;
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/api/research'))researchPosts++});
  await page.goto('/');await page.locator('#matter-select').waitFor();
  await page.selectOption('#client-role','buyer');await page.selectOption('#client-goal','performance');await page.fill('#matter-name','合成UI测试案（非真实案件）');
  await page.click('#matter-create');await page.waitForFunction(()=>document.querySelector('#matter-select').value.length===32);
  await page.selectOption('#material-kind','contract');
  await page.locator('#case-files').setInputFiles({name:'合成合同.txt',mimeType:'text/plain',buffer:Buffer.from('本文件仅用于合成UI测试。合同记载交付日期为2026-10-01。','utf8')});
  await page.click('#material-upload');await page.locator('#matter-files input').waitFor();
  const payload=await page.evaluate(()=>window.workbenchPayload());assert.equal(payload.client_profile.goal,'performance');assert.equal(payload.client_profile.client_role,'buyer');assert.equal(payload.material_ids.length,1);assert.equal(researchPosts,0);
  assert.ok((await page.locator('#matter-files').innerText()).includes('合成合同.txt'));
  await page.screenshot({path:path.join(root,'intake-desktop.png'),fullPage:false});
  let reportCheck=null;
  if(fs.existsSync(path.join(root,'focused-job.json'))){
   const job=JSON.parse(fs.readFileSync(path.join(root,fs.existsSync(path.join(root,'guard-replay-job.json'))?'guard-replay-job.json':'focused-job.json'),'utf8'));
   await page.goto('/#job='+job.id);await page.locator('#report h1').waitFor({timeout:30000});
   const text=await page.locator('#report').innerText();assert.ok(text.includes('处理方案比较'));assert.ok(text.includes('案件材料与证据链'));assert.ok(text.includes('不作排序或唯一推荐'));assert.ok(text.includes('未重新'));
   assert.ok((await page.locator('#title').innerText()).includes('待核验'));
   assert.equal(await page.locator('#client-goal').inputValue(),'undecided');assert.equal(await page.locator('#matter-files input').count(),0);
   for(const c of job.result.verification.checks.filter(c=>c.status!=='supported'))assert.ok(!text.includes(c.statement),'rejected claim leaked '+c.claim_id);
   await page.locator('#report h2').filter({hasText:'处理方案比较'}).evaluate(n=>n.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(root,'options-desktop.png'),fullPage:false});
   const citation=page.locator('#report .citation').first();const ref=await citation.getAttribute('data-ref');await citation.click();assert.ok(await page.locator('[id="'+ref+'"]').isVisible());
   const downloadPromise=page.waitForEvent('download');await page.click('#download');const download=await downloadPromise;const exportPath=path.join(root,'focused-export.md');await download.saveAs(exportPath);const exported=fs.readFileSync(exportPath,'utf8');assert.ok(exported.includes(job.result.report));assert.ok(exported.includes('案卷与方案核验'));assert.ok(!exported.includes('\uFFFD'));
   // Material source navigation is a separate UI fixture, never claimed as fresh legal research.
   const material={id:'Ufixture_1',doc_type:'material',title:'合成材料 · 段落 1',text:'仅为UI来源卡片测试。',location:'段落 1',material_id:'fixture'};
   await page.evaluate(({r,m})=>{r=JSON.parse(JSON.stringify(r));r.evidence.push(m);r.report+='\n\n## UI合成来源检查\n\n材料记载尚待核实 ['+m.id+']';showResult(r)},{r:job.result,m:material});
   await page.locator('.citation[data-ref="Ufixture_1"]').click();assert.ok(await page.locator('#Ufixture_1').isVisible());assert.equal(await page.locator('#Ufixture_1 a').count(),0);
   reportCheck={job_id:job.id,rejected_units_hidden:true,source_navigation:true,material_source_fixture:true,export_complete:true};
  }
  assert.deepEqual(errors,[]);assert.equal(researchPosts,0);
  fs.writeFileSync(path.join(root,'ui-validation.json'),JSON.stringify({passed:true,intake_case_id:payload.matter_id,uploaded_materials:payload.material_ids,client_goal_payload:true,report:reportCheck,page_errors:errors,new_research_posts:researchPosts},null,2)+'\n','utf8');
  console.log('PASS: local intake, selection, goal payload, no unintended research; report checks='+Boolean(reportCheck));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
