import json,re
from collections import defaultdict,Counter
import corpus
from official_bulk import dump
with corpus.connection() as db:docs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM documents WHERE doc_type='law'")]
groups=defaultdict(list)
for d in docs:groups[(d['law_name'],d.get('version'),d['url'])].append(d)
rows=[]
for (name,version,url),ds in groups.items():
 d=ds[0];rows.append(dict(name=name,version=version,url=url,records=len(ds),ids=[x['id'] for x in ds],published=d.get('published_at'),version_note=d.get('version_note'),status=d.get('validity',{}).get('code'),raw_path=d.get('raw_path')))
dump(corpus.DATA/'validity-all-inventory.json',rows)
print('DOCS',len(docs),'SOURCE_VERSIONS',len(rows),'NAMES',len({d['law_name'] for d in docs}))
print('JUDICIAL')
for r in rows:
 if r['ids'][0].startswith('J'):print(json.dumps({k:r[k] for k in ('name','version','records','url','status')},ensure_ascii=False))
