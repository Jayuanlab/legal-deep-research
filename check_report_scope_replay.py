"""Replay observed scope failures against program guards, without another LLM call."""
import json
from pathlib import Path
from unittest.mock import patch
from corpus import connection
from vectors import chunks
from research_engine import validate_claims,Budget
from official_bulk import dump
out=Path(__file__).parent/'runs/report-v2'
j=json.loads((out/'pre-scope-guard-job.json').read_text(encoding='utf-8'))
checks=next(e['checks'] for e in j['events'] if e['stage_key']=='verify' and 'checks' in e)
selected=[c for c in checks if c['claim_id'] in ('K2','K5','K7')]
assert len(selected)==3 and all(c['status']=='supported' for c in selected)
ids={ref['source_id'] for c in selected for ref in c['references']}
with connection() as db:docs=[json.loads(row[0]) for row in db.execute('SELECT payload FROM documents')]
evidence=[dict(d,id=p['id'],text=p['text']) for d in docs for p in chunks(d) if p['id'] in ids]
claims=[dict(c,id=c['claim_id']) for c in selected]
with patch('research_engine.complete') as model:
 result=validate_claims(claims,evidence,Budget(),question=j['question'])
model.assert_not_called()
assert result['accepted']==0
assert all(c['status']=='unsupported' for c in result['checks'])
dump(out/'scope-replay-validation.json',dict(passed=True,diagnostic_job=j['id'],originally_model_accepted=3,program_rejected=3,new_model_calls=0,checks=result['checks']))
print('PASS: all three observed model-approved deadline errors rejected before LLM verification')
