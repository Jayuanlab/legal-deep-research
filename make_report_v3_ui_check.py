from pathlib import Path
root=Path(__file__).parent
s=(root/'check-report-v2-live.cjs').read_text(encoding='utf-8')
s=s.replace('runs/report-v2','runs/report-v3').replace('candidate-job.json','reviewed-job.json').replace('candidate-','reviewed-').replace("'结论摘要','事实与材料基础'","'事实材料台账','解除通知的行使与生效','结论摘要','事实与材料基础'")
needle="  const citation=page.locator('#report .citation').first()"
extra="""  assert.ok(await page.locator('#report .citation[data-ref=\"E565\"]').count()>0);
  await page.locator('#report h3').filter({hasText:'事实材料台账'}).evaluate(n=>n.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(root,'reviewed-ledger.png'),fullPage:false});
  await page.locator('#report h4').filter({hasText:'解除通知的行使与生效'}).first().evaluate(n=>n.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(root,'reviewed-notice.png'),fullPage:false});
"""
assert needle in s
s=s.replace(needle,extra+needle)
(root/'check-report-v3-live.cjs').write_text(s,encoding='utf-8')
