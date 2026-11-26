import json
from collect_gap185 import OUT,read_source,ARTICLE,clean_text
rows=[]
for p in (OUT/'parsed').glob('*.json'):
 r=json.loads(p.read_text(encoding='utf-8'))
 try:
  vs,*_=read_source(r['url'])
  counts=[len(ARTICLE.findall(clean_text(t))) for t,s in vs]
  mx=max(counts)
  if r['article_count'] and mx>r['article_count']:rows.append(dict(name=r['name'],stored=r['article_count'],maximum=mx,url=r['url']))
 except Exception as e:print(type(e).__name__)
print(json.dumps(rows,ensure_ascii=False,indent=2))
