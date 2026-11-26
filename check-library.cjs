const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8765');
  await page.locator('#corpus').click();await page.locator('#library-content .evidence-item').first().waitFor();
  await page.locator('#library-topic option[value="婚姻家庭"]').waitFor({state:'attached'});
  await page.locator('#library-topic').selectOption('婚姻家庭');
  await page.waitForFunction(()=>document.querySelector('#library-summary').textContent.includes('匹配 79 条'));
  await page.locator('#library-query').fill('离婚');await page.locator('#library-form button').click();
  await page.waitForFunction(()=>document.querySelector('#library-content').textContent.includes('离婚'));
  assert.ok(await page.locator('#library-content .evidence-item').count()>0);
  await page.screenshot({path:require('node:path').join(__dirname,'library-desktop.png')});
  await page.locator('#library-type').selectOption('case');
  await page.locator('#library-query').fill('');await page.locator('#library-form button').click();
  await page.waitForFunction(()=>document.querySelector('#library-summary').textContent.includes('匹配 278 条'));
  assert.equal(await page.locator('#library-topic').isDisabled(),false);
  await page.locator('#library-query').fill('隆昌伟业');await page.locator('#library-form button').click();
  await page.waitForFunction(()=>document.querySelector('#library-content').textContent.includes('指导案例166'));
  assert.ok(await page.locator('#library-content details').count()>0);
  await page.screenshot({path:require('node:path').join(__dirname,'library-cases-desktop.png')});
  assert.deepEqual(errors,[]);
  console.log('PASS: expanded catalog, civil topic filtering, divorce keyword search, case library isolation, desktop layout');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
