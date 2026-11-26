"""Replay the exact observed claim through the production validator, no fixtures."""
import json
from pathlib import Path
from research_engine import Budget,validate_claims

out=Path(__file__).parent/'runs'
old=json.loads((out/'a90c2c658fb14c779286758dbb3fd0ef.json').read_text(encoding='utf-8'))
result=old['result'];prior=next(c for c in result['verification']['checks'] if c['issue_id']=='I4')
claim=dict(id=prior['claim_id'],issue_id=prior['issue_id'],statement=prior['statement'],references=prior['references'])
budget=Budget()
check=validate_claims([claim],result['evidence'],budget,question=old['question'],assessment=result['assessment'])
assert prior['status']=='supported' and check['accepted']==0
assert check['checks'][0]['fact_status']=='unestablished'
assert budget.calls==0,'This observed contradiction must be blocked before calling the model'
record=dict(source_job=old['id'],question=old['question'],original=prior,replayed=check,budget=budget.snapshot(),
            method='原始主张与原始证据原样回放；生产验证器程序检查直接拦截，未调用模型或联网检索。')
(out/'privacy-replay.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(before=prior['status'],after=check['checks'][0]['status'],reason=check['checks'][0]['reason'],model_calls=budget.calls),ensure_ascii=False))
