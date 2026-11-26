const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  let allow=false,cancelled=false,starts=0;
  const id='f'.repeat(32);
  await page.route('**/api/research/jobs**',async route=>{
   const req=route.request(),url=new URL(req.url());
   if(url.pathname.endsWith('/cancel')){cancelled=true;return route.fulfill({json:{id,status:'running'}})}
   if(req.method()==='POST'){starts++;return route.fulfill({status:202,json:{id,status:'queued'}})}
   if(!allow)return route.abort('failed');
   return route.fulfill({json:{id,question:'contract test',status:cancelled?'cancelled':'running',error:cancelled?'cancelled by user':undefined,events:[]}});
  });
  await page.goto('http://127.0.0.1:8765');await page.locator('#submit').click();
  await page.waitForFunction(()=>document.querySelector('#submit').textContent==='继续查看');
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('legal-active-job')),id);
  assert.equal(await page.locator('#cancel').isVisible(),true);
  allow=true;await page.locator('#submit').click();await page.locator('#cancel').click();
  await page.waitForFunction(()=>!document.querySelector('#submit').disabled&&document.querySelector('#cancel').hidden);
  assert.equal(starts,1);assert.equal(cancelled,true);
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('legal-active-job')),null);
  assert.match(await page.locator('#error').innerText(),/cancelled/);
  console.log('PASS: polling failure retains task, resume avoids duplicate submission, cancellation reaches terminal state');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
