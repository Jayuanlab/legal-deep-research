import json,time,statistics,os
import corpus,vectors
from official_bulk import ROOT,dump
from models import embedding_identity
corpus.DB=corpus.DATA/'legal-gap185.sqlite3'
targets=json.loads((corpus.DATA/'gap185-targets.json').read_text(encoding='utf-8'))
docs=json.loads((corpus.DATA/'laws-gap185.json').read_text(encoding='utf-8'))
loc=[]
for i,t in enumerate(targets,1):
 name=t['name'];eligible=any(d['law_name']==name and d.get('reference_status')!='not_reference' for d in docs)
 rows=corpus.library(name,'law',size=4)['items']
 loc.append(dict(name=name,eligible=eligible,hit=any(d.get('law_name')==name for d in rows),returned=[dict(id=d['id'],name=d.get('law_name')) for d in rows]))
 if i%25==0:print('LOCATORS',i,flush=True)
dump(ROOT/'evaluation/gap185-locators.json',dict(rows=loc,eligible=sum(r['eligible'] for r in loc),hits=sum(r['hit'] for r in loc),excluded=[r['name'] for r in loc if not r['eligible']],scope='185项目录关键词AND定位，调用资料浏览接口，包含仅存档项；不等于语义问题召回率'))
if os.environ.get('LEGAL_LOCATORS_ONLY')=='1':raise SystemExit(0)
queries=json.loads((ROOT/'evaluation/gap185-smoke-queries.json').read_text(encoding='utf-8'))
details=[]
for i,q in enumerate(queries,1):
 start=time.monotonic()
 try:
  rows=vectors.retrieve(q['query']);law=[d for d in rows if d['doc_type']=='law'];ids=[d['parent_id'] for d in law]
  details.append(dict(**q,hit=bool(set(ids)&set(q['expected_ids'])),law_hit=any(d.get('law_name')==q['expected_law'] for d in law),seconds=round(time.monotonic()-start,2),returned=[dict(id=d['id'],parent_id=d['parent_id'],title=d['title'],text=d['text']) for d in rows]))
 except Exception as e:details.append(dict(**q,hit=False,error=type(e).__name__,seconds=round(time.monotonic()-start,2)))
 print('SCENARIO',i,details[-1]['hit'],details[-1]['seconds'],flush=True)
 dump(ROOT/'evaluation/gap185-smoke.json',dict(embedding_identity=embedding_identity(),corpus=corpus.stats(),queries=len(details),hits=sum(r['hit'] for r in details),details=details,scope='真实阿里云查询向量+本地全文分片向量/BM25/RRF，每题法条Top4；未重跑原400题，也不衡量法律结论正确率'))
