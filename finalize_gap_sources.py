import json
from collect_gap185 import ROOT,OUT,dump
rs=[json.loads(p.read_text(encoding='utf-8')) for p in (OUT/'parsed').glob('*.json')]
dump(ROOT/'data/gap185-priority-sources.json',[dict(name=r['name'],title=r['name'],url=r['url']) for r in rs])
path=ROOT/'data/gap185-extraction-overrides.json'
rules=json.loads(path.read_text(encoding='utf-8'))
for rule in rules:
 if rule['url'].startswith('https://www.fujian.gov.cn/'):
  rule.update(directory_title_binding='目录标题与同页1978-05-24批准决议正文对应；未将附件条文归入决议',source_page_status='省政府页面标为废止、失效；其标注对象为页面通知，决议适用状态尚须核验')
dump(path,rules)
print('Pinned',len(rs),'archived official source selections')
