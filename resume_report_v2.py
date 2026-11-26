"""Continue the recorded same-question run at its failed repair checkpoint.

Keeps its parent immutable. Reuses only recorded retrieval hits and model verdicts;
new/rejected paragraphs go through real-model drafting and validation.
"""
import json,re,time,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path
from corpus import connection
from vectors import chunks
from research_jobs import get_job,save,now
from research_engine import Budget,repair_verified,render,quality,quote_check,structural_errors
from report_document import VERSION
from models import public_config
from official_bulk import dump
root=Path(__file__).parent;out=root/'runs/report-v2'
parent=get_job((out/'candidate-job-id.txt').read_text().strip())
assert parent['status'] in ('failed','completed')
dump(out/('recovery-parent-'+parent['id']+'.json'),parent)
if not (out/'repair-parent-job.json').exists():
 dump(out/'repair-parent-job.json',parent)
 (out/'repair-parent-job-id.txt').write_text(parent['id'],encoding='utf-8')
issues=next(e['issues'] for e in parent['events'] if 'issues' in e)
plan=dict(issues=issues,missing_facts=[])
coverage=[e['coverage'] for e in parent['events'] if e.get('stage_key')=='assess' and 'coverage' in e][-1]
assessment=dict(coverage=coverage,sufficient=all(c['sufficient'] for c in coverage),queries=[],missing_facts=[])
checks=[e['checks'] for e in parent['events'] if 'checks' in e][-1]
hits={}
for event in parent['events']:
 if not event.get('source_ids'):continue
 ids=[i['id'] for i in issues if i['query']==event.get('query')]
 for key in event['source_ids']:
  hits.setdefault(key,[])
  hits[key]=list(dict.fromkeys(hits[key]+ids))
with connection() as db:docs=[json.loads(row[0]) for row in db.execute('SELECT payload FROM documents')]
evidence=[dict(doc,id=p['id'],parent_id=doc['id'],text=p['text'],retrieval_issues=hits[p['id']],fragment=dict(index=p['index'],start=p['start'],end=p['end'],source_length=len(doc['text']))) for doc in docs for p in chunks(doc) if p['id'] in hits]
assert len(evidence)==len(hits)
sources={d['id']:d for d in evidence}
assert all(quote_check(ref,sources) is None for c in checks for ref in c['references'])
prior=dict(checks=checks,cited=sorted({ref['source_id'] for c in checks if c['status']=='supported' for ref in c['references']}),invalid=[],queries=[],accepted=sum(c['status']=='supported' for c in checks),passed=False,status='部分主张未获证据支持',scope='逐字引文、事实前提与模型法律支持性检查；定点程序规则补充拦截已观察到的期限适用错误，不能替代人工复核。')
key=uuid.uuid4().hex
payload=dict(question=parent['question'],parent_job=parent['id'],events=list(parent['events']))
with connection() as db:db.execute('INSERT INTO research_jobs(id,status,payload,updated_at) VALUES(?,?,?,?)',(key,'running',json.dumps(payload,ensure_ascii=False),now()))
(out/'candidate-job-id.txt').write_text(key,encoding='utf-8')
started=time.monotonic();budget=Budget(seconds=300,max_calls=8,max_output_tokens=16000,max_input_chars=250000)
def event(stage,detail,state='completed',**extra):
 row=dict(stage=stage,stage_key='verify' if stage=='引用验证' else 'draft',detail=detail,state=state,elapsed=round(time.monotonic()-started,2),elapsed_scope='恢复阶段',**extra)
 payload['events'].append(row);save(key,payload,'running')
print(json.dumps(dict(id=key,parent=parent['id'],status='resuming',reused_evidence=len(evidence)),ensure_ascii=False),flush=True)
try:
 event('报告生成','从父任务失败的修订检查点继续；复用有来源可追溯的检索与核验记录，仅修订未通过的类型。','running')
 verification=repair_verified(parent['question'],plan,evidence,assessment,prior,budget)
 event('引用验证',verification['status'],'completed' if verification['passed'] else 'limited',checks=verification['checks'])
 q=quality(plan,verification,evidence);verification['uncited']=[d['id'] for d in evidence if d['id'] not in verification['cited']]
 outcome='complete' if verification['passed'] and q['passed'] and assessment['sufficient'] else 'limited'
 stop='研究流程含故障续跑，修订单元重新核验；父任务历史保持原样。'
 document=dict(report_version=2,facts=[],claims=[])
 report=render(plan,assessment,verification,[],stop,document,evidence,parent['question'])
 # Exact start time is present in this server log's unique research POST.
 log=(root/'server-report-v2-final-error.log').read_text(encoding='utf-8')
 stamp=re.search(r'\[([^]]+)\] "POST /api/research/jobs HTTP/1.1" 202',log).group(1)
 origin=datetime.strptime(stamp,'%d/%b/%Y %H:%M:%S').replace(tzinfo=timezone(timedelta(hours=8)))
 elapsed=round((datetime.now(timezone.utc)-origin).total_seconds(),2)
 result=dict(question=parent['question'],report_version=VERSION,report_quality=q,facts=[],plan=[i['question'] for i in issues],research_plan=plan,assessment=assessment,evidence=evidence,report=report,verification=verification,retrieval_mode='hybrid',retrieval_warning=None,events=payload['events'],mode=public_config()['text_model'],elapsed=elapsed,outcome=outcome,stop_reason=stop,supplement_rounds=max(e.get('round',0) for e in parent['events']),budget=budget.snapshot(),budget_scope='仅恢复阶段；失败父任务未保存预算快照，不将其忽略后宣称这是累计调用或Token量。',recovery=dict(parent_job=parent['id'],reused_retrieval=True,reconstructed_fragments_verified=True,earlier_fact_ledger_not_persisted=True,elapsed_scope='从父任务POST到本次完成的墙钟时间，包含故障后的诊断与恢复等待',resume_elapsed=round(time.monotonic()-started,2)))
 payload['result']=result;save(key,payload,'completed');dump(out/'candidate-job.json',get_job(key));(out/'candidate-report.md').write_text(report,encoding='utf-8')
 print(json.dumps(dict(id=key,status='completed',outcome=outcome,accepted=verification['accepted'],quality=q),ensure_ascii=False),flush=True)
except Exception as error:
 payload['error']=str(error);save(key,payload,'failed');raise
