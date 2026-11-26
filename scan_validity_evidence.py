"""Examine every local source/version for explicit repeal and amendment evidence."""
import json,re
from collections import defaultdict
import corpus
from official_bulk import dump
from law_validity import norm
with corpus.connection() as db:docs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM documents WHERE doc_type='law'")]
groups=defaultdict(list)
for d in docs:groups[(d['law_name'],d.get('version'),d['url'])].append(d)
names={norm(d['law_name']):d['law_name'] for d in docs}
out=[];amend=[]
for key,ds in groups.items():
 for d in ds:
  text=d['text']
  if not any(w in text for w in ('同时废止','予以废止','废止下列','废止《')):continue
  for sentence in re.split('[。\n]',text):
   if not any(w in sentence for w in ('同时废止','予以废止','废止下列','废止《')):continue
   for canonical,name in names.items():
    if canonical in norm(sentence) and canonical!=norm(key[0]):
     out.append(dict(source_id=d['id'],source_name=key[0],source_url=d['url'],target=name,quote=sentence,effective=d.get('date'),published=d.get('published_at'),source_version=key[1]))
dump(corpus.DATA/'validity-explicit-candidates.json',out)
print('SOURCES',len(groups),'EXPLICIT_CANDIDATES',len(out))
for r in out:print(json.dumps(r,ensure_ascii=False))
