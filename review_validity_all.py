import json
from collections import Counter,defaultdict
from pathlib import Path
import corpus
p=json.loads((corpus.DATA/'validity-all-proposal.json').read_text(encoding='utf-8'))
with corpus.connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
groups=defaultdict(list)
for k,r in p['by_id'].items():
 if r['code'] in ('superseded','partially_repealed','repealed'):groups[(docs[k]['law_name'],r['code'],r['source_url'])].append(k)
for (name,code,url),ids in groups.items():print(json.dumps(dict(name=name,code=code,count=len(ids),example=ids[0],url=url),ensure_ascii=False))
positives={q['doc_id'] for name in ('laws','cases','controls') for line in (Path('evaluation')/f'{name}.jsonl').read_text(encoding='utf-8').splitlines() for q in json.loads(line)['qrels']}
print('QREL_CONFLICTS',[(k,p['by_id'][k]['code']) for k in positives if p['by_id'].get(k,{}).get('code') in ('repealed','superseded','partially_repealed')])
