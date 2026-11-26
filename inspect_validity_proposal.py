import json
from collections import Counter,defaultdict
from pathlib import Path
p=json.loads(Path('data/validity-all-proposal.json').read_text(encoding='utf-8'))
group=defaultdict(list)
for k,r in p['by_id'].items():group[(r['code'],r.get('source_url'))].append(k)
print('BY_SOURCE',[(code,len(ids),u) for (code,u),ids in group.items() if code=='repealed'])
r=json.loads(Path('data/raw/bulk/validity/parsed/ecological-code-2026.json').read_text(encoding='utf-8'))
print('ECO END',repr(r['text'][-700:]));print('REPEAL_LOC',r['text'].find('同时废止'))
from validity_evidence import repeal_targets,canonical
import corpus
with corpus.connection() as db:names={canonical(json.loads(x[0])['law_name']) for x in db.execute("SELECT payload FROM documents WHERE doc_type='law'")}
for sentence in r['text'].split('。'):
 if '同时废止' in sentence:
  print('SENTENCE',repr(sentence[:900]));print('TARGETS',[(t['name'],canonical(t['name']) in names) for t in repeal_targets(sentence)])
