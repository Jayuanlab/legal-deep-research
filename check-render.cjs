const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  await page.goto('http://127.0.0.1:8765');
  await page.waitForFunction(()=>typeof renderReport==='function');
  const html=await page.evaluate(()=>renderReport('### Heading\nBody **bold** [E563] [C1001_2]\n<script>alert(1)</script>'));
  assert.ok(html.includes('<h3>Heading</h3><p>Body <strong>bold</strong>'));
  assert.ok(html.includes('data-ref="E563"'));
  assert.ok(html.includes('data-ref="C1001_2"'));
  assert.ok(!html.includes('<script>'));
  await page.locator('#corpus').click();
  await page.locator('#library-content .evidence-item').first().waitFor();
  await page.screenshot({path:require('node:path').join(__dirname,'library-desktop.png')});
  console.log('PASS: heading boundaries, emphasis, citation, HTML escaping, desktop library');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
