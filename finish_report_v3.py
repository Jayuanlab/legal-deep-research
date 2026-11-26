"""Finish this turn's fresh research from its saved verification checkpoint.

The failed root remains immutable. No v2 conclusions or retrieval hits are reused.
"""
import copy,json,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from corpus import connection
from research_jobs import get_job,save,now,cancelled
from research_engine import Budget,repair_verified,render,quality,quote_check
from report_ledger import ledger_quality
from notice_rules import notice_errors
from models import public_config
from official_bulk import dump
root=Path(__file__).parent;out=root/'runs/report-v3'
parent=get_job((out/'candidate-job-id.txt').read_text().strip())
assert parent['status']=='failed' and not parent.get('parent_job')
cp=copy.deepcopy(parent['checkpoint']);assert cp['question']==parent['question']
assert cp['document']['facts'] and cp['document']['materials'] and cp['verification']['checks']
dump(out/'root-job.json',parent)
key=uuid.uuid4().hex;payload=dict(question=parent['question'],parent_job=parent['id'],events=list(parent['events']))
with connection() as db:db.execute('INSERT INTO research_jobs(id,status,payload,updated_at) VALUES(?,?,?,?)',(key,'running',json.dumps(payload,ensure_ascii=False),now()))
(out/'reviewed-job-id.txt').write_text(key,encoding='utf-8')
started=time.monotonic();budget=Budget(seconds=300,max_calls=8,max_output_tokens=14000,max_input_chars=250000,cancelled=lambda:cancelled(key))
def event(stage,detail,state='completed',**extra):
 row=dict(stage=stage,stage_key='draft' if stage=='报告生成' else 'verify',detail=detail,state=state,elapsed=round(time.monotonic()-started,2),elapsed_scope='本轮检查点恢复阶段',**extra)
 payload['events'].append(row);save(key,payload,'running')
print(json.dumps(dict(id=key,parent=parent['id'],status='finishing_checkpoint',facts=len(cp['document']['facts']),materials=len(cp['document']['materials'])),ensure_ascii=False),flush=True)
try:
 sources={d['id']:d for d in cp['evidence']}
 assert all(quote_check(ref,sources) is None for c in cp['verification']['checks'] for ref in c['references'])
 event('报告生成','从本轮全新研究的核验检查点补完修订：丢弃未请求类型，补齐附期限通知的实际未履行条件。','running')
 v=repair_verified(cp['question'],cp['plan'],cp['evidence'],cp['assessment'],cp['verification'],budget)
 event('引用验证',v['status'],'completed' if v['passed'] else 'limited',checks=v['checks'])
 q=quality(cp['plan'],v,cp['evidence']);q['ledger']=ledger_quality(cp['document'],cp['plan'],v);q['passed']=q['passed'] and q['ledger']['passed']
 v['report_quality']=q;v['uncited']=[d['id'] for d in cp['evidence'] if d['id'] not in v['cited']]
 outcome='complete' if q['passed'] and v['passed'] and cp['assessment']['sufficient'] else 'limited'
 stop='本轮从拆题开始执行，最后修订失败后由该轮检查点补完；原始失败任务未改写。'
 report=render(cp['plan'],cp['assessment'],v,[],stop,cp['document'],cp['evidence'],cp['question'])
 change=json.loads((out/'change.json').read_text(encoding='utf-8'));origin=datetime.fromisoformat(change['started_at'])
 r=dict(question=cp['question'],report_version='legal-report-v3',mode=public_config()['text_model'],report=report,facts=cp['document']['facts'],materials=cp['document']['materials'],research_plan=cp['plan'],plan=[i['question'] for i in cp['plan']['issues']],assessment=cp['assessment'],verification=v,report_quality=q,evidence=cp['evidence'],events=payload['events'],outcome=outcome,stop_reason=stop,supplement_rounds=max(e.get('round',0) for e in parent['events']),retrieval_mode='hybrid',retrieval_warning=None,elapsed=round((datetime.now(timezone.utc)-origin).total_seconds(),2),budget=budget.snapshot(),budget_scope='仅本轮检查点恢复阶段；根任务核验前预算快照另存，失败修订后的累计预算未完整记录。',root_budget_checkpoint=cp['budget'],recovery=dict(root_job=parent['id'],root_started_fresh=True,used_v2_outputs=False,frozen_evidence=True,notice_condition_corrected=True,elapsed_scope='从本轮根任务启动到检查点恢复完成，含失败和诊断等待',resume_elapsed=round(time.monotonic()-started,2)))
 for c in v['checks']:
  if c['status']=='supported' and c.get('role')=='notice':assert not notice_errors(c,sources)
 payload['result']=r;payload['checkpoint']=dict(cp,verification=v,budget=budget.snapshot());save(key,payload,'completed')
 job=get_job(key);assert job['status']=='completed'
 dump(out/'reviewed-job.json',job);(out/'reviewed-report.md').write_text(report,encoding='utf-8')
 print(json.dumps(dict(id=key,status='completed',outcome=outcome,accepted=v['accepted'],quality=q),ensure_ascii=False),flush=True)
except Exception as error:
 payload['error']=str(error);save(key,payload,'failed');dump(out/'reviewed-job.json',get_job(key));raise
