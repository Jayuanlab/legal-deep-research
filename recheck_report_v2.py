"""Recheck one actual paragraph after fixing an overly strict program rule."""
import json,time,uuid
from pathlib import Path
from datetime import datetime,timezone,timedelta
from research_jobs import get_job,save,now
from corpus import connection
from research_engine import Budget,validate_claims,render,quality
from official_bulk import dump
out=Path(__file__).parent/'runs/report-v2'
parent=get_job((out/'candidate-job-id.txt').read_text().strip());assert parent['status']=='completed'
dump(out/('recovery-parent-'+parent['id']+'.json'),parent)
r=parent['result'];r=json.loads(json.dumps(r,ensure_ascii=False));rows=r['verification']['checks']
selected=[c for c in rows if c['issue_id']=='I1' and c.get('role')=='counterargument' and c['status']!='supported'];assert len(selected)==1
key=uuid.uuid4().hex;payload=dict(question=r['question'],parent_job=parent['id'],events=list(parent['events']))
with connection() as db:db.execute('INSERT INTO research_jobs(id,status,payload,updated_at) VALUES(?,?,?,?)',(key,'running',json.dumps(payload,ensure_ascii=False),now()))
(out/'candidate-job-id.txt').write_text(key,encoding='utf-8');start=time.monotonic();budget=Budget(seconds=150,max_calls=1,max_output_tokens=3000,max_input_chars=40000)
print(json.dumps(dict(id=key,parent=parent['id'],status='rechecking',claim=selected[0]['claim_id'])),flush=True)
try:
 checked=validate_claims([dict(c,id=c['claim_id']) for c in selected],r['evidence'],budget,r['question'],r['assessment'])
 replacement={c['claim_id']:c for c in checked['checks']}
 rows=[replacement.get(c['claim_id'],c) for c in rows];v=r['verification'];v['checks']=rows
 v.update(cited=sorted({ref['source_id'] for c in rows if c['status']=='supported' for ref in c['references']}),accepted=sum(c['status']=='supported' for c in rows),passed=all(c['status']=='supported' for c in rows))
 v['status']='主张引用检查通过' if v['passed'] else '部分主张未获证据支持';q=quality(r['research_plan'],v,r['evidence']);v['report_quality']=q;r['report_quality']=q
 r['outcome']='complete' if v['passed'] and q['passed'] and r['assessment']['sufficient'] else 'limited'
 event=dict(stage='引用验证',stage_key='verify',state='completed' if checked['passed'] else 'limited',detail='修正期限措辞规则误拦后，对原抗辩段落单独执行真实模型复核；其他内容不重写。',checks=checked['checks'],elapsed=round(time.monotonic()-start,2),elapsed_scope='原文复核阶段')
 payload['events'].append(event);r['events']=payload['events'];r['recovery']['parent_job']=parent['id'];r['recovery']['original_paragraph_rechecked']=True
 r['recovery']['latest_check_budget']=budget.snapshot();r['budget_scope']='仅前次局部恢复的预算；本次原文复核预算另存recovery.latest_check_budget，失败父任务累计预算未知。'
 r['stop_reason']='完整流程含故障续跑与原文复核；未通过的类案单元排除，父任务历史保持原样。'
 r['report']=render(r['research_plan'],r['assessment'],v,[],r['stop_reason'],dict(facts=[]),r['evidence'],r['question'])
 # Keep the same original wall-clock origin used by the preceding recovery.
 finished=datetime.fromisoformat(parent['updated_at']);r['elapsed']=round(r['elapsed']+(datetime.now(timezone.utc)-finished).total_seconds(),2)
 payload['result']=r;save(key,payload,'completed');dump(out/'candidate-job.json',get_job(key));(out/'candidate-report.md').write_text(r['report'],encoding='utf-8')
 print(json.dumps(dict(id=key,status='completed',outcome=r['outcome'],accepted=v['accepted'],quality=q),ensure_ascii=False),flush=True)
except Exception as error:
 payload['error']=str(error);save(key,payload,'failed');raise
