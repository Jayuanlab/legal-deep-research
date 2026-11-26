"""Recheck the frozen real-model failure outputs after deterministic guard fixes."""
import copy,json,uuid
from pathlib import Path
from unittest.mock import patch
from corpus import connection
from research_engine import Budget
from research_jobs import now
from case_research import research_case
from matter_evidence import prepare_context
from report_review import factual_assertion_errors,legal_condition_errors

root=Path(__file__).parent/'runs'/'workbench-v4'
original=json.loads((root/'focused-job.json').read_text(encoding='utf-8'))
extraction=json.loads((root/'real-material-extraction.json').read_text(encoding='utf-8'))
base=json.loads((root/'baseline'/'reviewed-job.json').read_text(encoding='utf-8'))['result']
question=base['question'];sources={d['id']:d for d in base['evidence']}
class FrozenReply(Budget):
 def ask(self,instruction,payload,tokens):
  if 'observations' in instruction:return dict(observations=extraction['observations'])
  return dict(flags=original['result']['verification']['consistency_review']['flags'])

snapshot=dict(name=extraction['matter_name'],documents=[dict(extraction['documents'][0],spans=extraction['material_spans'])])
context=prepare_context(question,snapshot,FrozenReply())
assert len(context['observations'])==3 and len(context['rejected_observations'])==1
assert not any(o['slot']=='notice_arrival' for o in context['observations'])
(root/'guarded-material-extraction.json').write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
blocked=[]
for c in base['verification']['checks']:
 errors=factual_assertion_errors(c['statement'],question)+legal_condition_errors(c,sources)
 if errors:c.update(status='uncertain',reason='；'.join(errors));blocked.append(c['claim_id'])
options=copy.deepcopy(original['result']['strategy_verification'])
with patch('case_research.legal_research',return_value=base),patch('case_research.strategies',return_value=options):
 result=research_case(question,budget=FrozenReply())
review=result['verification']['consistency_review']
assert review['flags']==[] and len(review['rejected_flags'])==2
scope='真实模型输出冻结重放：重新运行修正后的材料与复核护栏；沿用旧报告冻结证据，未重新拆题、召回、补检索或发起新模型调用。'
result.update(validation_scope=scope,mode='真实模型输出冻结重放（护栏修正验证）')
result['report']='> 验证说明：'+scope+'\n\n'+result['report']
key=uuid.uuid4().hex;job=dict(question=question,result=result,events=result['events'],validation_scope=scope)
with connection() as db:db.execute('INSERT INTO research_jobs(id,status,payload,updated_at,cancel_requested) VALUES(?,?,?,?,0)',(key,'completed',json.dumps(job,ensure_ascii=False),now()))
job.update(id=key,status='completed')
(root/'guard-replay-job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
(root/'guard-replay-report.md').write_text(result['report'],encoding='utf-8')
summary=dict(scope=scope,job_id=key,original_real_model_calls=original['result']['budget']['model_calls'],new_model_calls=0,accepted_material_statements=len(context['observations']),unresolved_differences=len(context['differences']),rejected_material_statements=context['rejected_observations'],old_report_blocks=blocked,rejected_review_flags=review['rejected_flags'],outcome=result['outcome'],review_status=result['review_status'])
(root/'guard-replay-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(job_id=key,material_statements=3,rejected_arrival=1,rejected_review_flags=2,outcome=result['outcome'])))
