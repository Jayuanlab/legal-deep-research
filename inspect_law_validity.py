import corpus,json
from collections import Counter
with corpus.connection() as db:docs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM documents WHERE doc_type='law'")]
print('FIELDS',Counter(k for d in docs for k in d if 'status' in k or 'valid' in k))
seen=set()
for d in docs:
 key=(d['law_name'],d.get('authority_status'),d.get('reference_status'))
 if key in seen:continue
 seen.add(key)
 if d.get('reference_status')=='not_reference' or any(s in d.get('authority_status','') for s in ['已废止','已修改','失效']):
  print(json.dumps({k:d.get(k) for k in ['id','law_name','article','version','date','authority_status','reference_status','status_notice','status_url','historical_law_note']},ensure_ascii=False))
