import json,re
from collections import defaultdict
import corpus

def norm(s):return re.sub(r'[\s《》〈〉“”"（）()〔〕\[\]：:]','',s)
with corpus.connection() as db:docs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM documents WHERE doc_type='law'")]
source=json.loads((corpus.DATA/'law-validity-repeal-source.json').read_text(encoding='utf-8'))
rows={norm(r[1]):r for r in source['rows']}
matches=defaultdict(list)
for d in docs:
 row=rows.get(norm(d['law_name']))
 if row:matches[d['law_name']].append(d)
qrels={q['doc_id'] for f in ['laws','cases','controls'] for line in (corpus.DATA.parent/'evaluation'/f'{f}.jsonl').read_text(encoding='utf-8').splitlines() for q in json.loads(line)['qrels']}
for name,ds in matches.items():
 row=rows[norm(name)];d=ds[0]
 print(json.dumps(dict(name=name,count=len(ds),repealed_issue=row[2],version=d.get('version'),published=d.get('published_at'),head=d.get('version_note','')[:900],qrels=[x['id'] for x in ds if x['id'] in qrels]),ensure_ascii=False))
