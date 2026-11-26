import json,re,hashlib
from pathlib import Path
from research_jobs import get_job
from official_bulk import dump
root=Path(__file__).parent;out=root/'runs/report-v2'
job=json.loads((out/'candidate-job.json').read_text(encoding='utf-8'));r=job['result']
assert job['status']=='completed' and r['report_quality']['passed'] and r['verification']['accepted']==18
assert json.loads((out/'live-ui-validation.json').read_text(encoding='utf-8'))['passed']
assert 'Ran 131 tests' in (root/'report-v2-tests.log').read_text(encoding='utf-8')
assert (root/'report-v2-tests.log').read_text(encoding='utf-8').strip().endswith('OK')
chain=[];p=job
while p.get('parent_job'):
 p=get_job(p['parent_job']);chain.append(p['id']);dump(out/('recovery-parent-'+p['id']+'.json'),p)
failed=get_job((out/'failed-recovery-job-id.txt').read_text().strip());dump(out/'failed-recovery-job.json',failed)
change=json.loads((out/'change.json').read_text(encoding='utf-8'))
change.update(candidate_job=job['id'],root_research_job=chain[-1],recovery_chain=chain,rollout='已重启常驻服务加载本次最终代码；历史任务不改写',acceptance=dict(structure_passed=True,accepted_units=18,excluded_units=1,case_comparisons=2,regression_tests=131,actual_ui_and_export_passed=True),evaluation='同题比较含故障续跑与人工诊断等待，累计失败请求预算未完整保存，不能用来推断速度或总体法律准确率提升',candidate_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ('research_engine.py','report_document.py','server.py','app.js')})
dump(out/'change.json',change)
dump(out/'acceptance-result.json',dict(job_id=job['id'],question_identical=True,roles=r['report_quality'],outcome=r['outcome'],accepted=18,excluded=1,case_comparisons=2,regression_tests=131,quote_and_publication_checks='comparison.json',ui='live-ui-validation.json',scope_replay='scope-replay-validation.json',recovery_chain=chain,limitations=['规范效力仍有待核验标记','本次恢复未取得旧任务事实清单，facts为空','尚未充分展开解除通知生效步骤','单题观察不能代表普遍准确率，模型语义审查仍可能漏判']))
print(json.dumps(dict(final_job=job['id'],parents=chain,accepted=18,excluded=1,tests=131),ensure_ascii=False))
