"""Focused real-model validation; frozen V3 retrieval is replayed, never called fresh."""
import copy,json,time,uuid
from pathlib import Path
from unittest.mock import patch
from corpus import connection
from research_engine import Budget
from report_review import factual_assertion_errors,legal_condition_errors
from matter_evidence import prepare_context
from case_research import research_case
from research_jobs import now

ROOT=Path(__file__).parent/'runs'/'workbench-v4'
ROOT.mkdir(exist_ok=True,parents=True)
baseline=json.loads((ROOT.parent/'report-v3'/'reviewed-job.json').read_text(encoding='utf-8'))
(ROOT/'baseline'/'reviewed-job.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
base=copy.deepcopy(baseline.get('result',baseline));question=base['question']
budget=Budget(seconds=600,max_calls=10)
summary=dict(scope='新增模块真实模型验证＋旧报告冻结证据重放；未重新执行拆题、召回、补检索或旧主张的全量语义核验。',question=question,synthetic_materials=True)
spans=[dict(id='Udemo_1',material_id='demo',name='合成合同.txt',location='段落 1',text='本文件仅为合成测试材料，不是真实案件。合同记载交付期限为2026-10-01。买方记录：尚未实施替代交易。'),dict(id='Udemo_2',material_id='demo',name='合成合同.txt',location='段落 2',text='补充协议记载交付期限为2026-10-15。解除通知于2026-11-01寄出，未提供签收记录。')]
snapshot=dict(name='合成边界测试，不是真实案件',documents=[dict(id='demo',name='合成合同.txt',kind='contract',sha256='synthetic',status='text_extracted_unverified',spans=spans)])
try:
 print('REAL material extraction started',flush=True)
 context=prepare_context(question,snapshot,budget)
 (ROOT/'real-material-extraction.json').write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf-8')
 summary['material_extraction']=dict(observations=len(context['observations']),differences=context['differences'],rejected=len(context.get('rejected_observations',[])))
 print('REAL material extraction completed',flush=True)
 sources={d['id']:d for d in base['evidence']};blocked=[]
 for c in base['verification']['checks']:
  errors=factual_assertion_errors(c['statement'],question)+legal_condition_errors(c,sources)
  if errors:
   c.update(status='uncertain',reason='；'.join(errors));blocked.append(dict(claim_id=c['claim_id'],role=c.get('role'),errors=errors))
 base['verification']['accepted']=sum(c['status']=='supported' for c in base['verification']['checks'])
 base['verification']['passed']=all(c['status']=='supported' for c in base['verification']['checks'])
 summary['old_report_regression_blocks']=blocked
 print('Frozen baseline guards blocked: '+','.join(c['claim_id'] for c in blocked),flush=True)
 print('REAL options, support validation and consistency review started',flush=True)
 with patch('case_research.legal_research',return_value=base):
  result=research_case(question,budget=budget,emit=lambda e:print(e['stage']+': '+e['detail'],flush=True))
 result['validation_scope']=summary['scope'];result['mode']='真实模型新增模块验证＋冻结证据重放'
 result['report']='> 验证说明：'+summary['scope']+'\n\n'+result['report']
 key=uuid.uuid4().hex;job=dict(question=question,result=result,events=result['events'],validation_scope=summary['scope'])
 with connection() as db:db.execute('INSERT INTO research_jobs(id,status,payload,updated_at,cancel_requested) VALUES(?,?,?,?,0)',(key,'completed',json.dumps(job,ensure_ascii=False),now()))
 job.update(id=key,status='completed');(ROOT/'focused-job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'focused-report.md').write_text(result['report'],encoding='utf-8')
 summary.update(job_id=key,outcome=result['outcome'],review_status=result['review_status'],strategy_checks=[dict(claim_id=c['claim_id'],option_key=c.get('option_key'),status=c['status'],reason=c.get('reason')) for c in result['strategy_verification']['checks']],consistency_review=result['verification'].get('consistency_review'),budget=budget.snapshot())
 print('Focused validation completed; job '+key,flush=True)
except Exception as e:
 summary.update(error_type=type(e).__name__,error=str(e),budget=budget.snapshot());raise
finally:
 (ROOT/'focused-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
