import json,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
import requests
from official_bulk import dump
from research_engine import Budget
root=Path(__file__).parent;out=root/'runs/report-v3';base='http://127.0.0.1:8765'
if sys.argv[1]=='start':
 assert not (out/'candidate-job-id.txt').exists(),'Poll the recorded job; do not duplicate it'
 health=requests.get(base+'/api/health',timeout=30).json();assert health['report_version']=='legal-report-v3' and health['vectors']['ready']
 old=json.loads((out/'baseline-job.json').read_text(encoding='utf-8'))
 response=requests.post(base+'/api/research/jobs',json=dict(question=old['question']),timeout=20);response.raise_for_status();job=response.json()
 (out/'candidate-job-id.txt').write_text(job['id'],encoding='utf-8')
 dump(out/'change.json',dict(change_id='notice-ledger-v3-20261113',authorization='用户明确要求补齐解除通知方式、生效及事实材料台账，从头重跑相同问题并评估不足',started_at=datetime.now(timezone.utc).isoformat(),baseline_job=old['id'],candidate_job=job['id'],fresh_run=True,question=old['question'],health=health,budget_limits=Budget().snapshot()['limits'],candidate_hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ('research_engine.py','report_document.py','report_ledger.py','notice_rules.py','research_jobs.py','app.js')},hypothesis='程序强制规范覆盖、独立材料台账及通知分析类型能够使本题获得三条解除路径和与已核验分析关联的补证任务；若来源不足、台账缺项或逐段核验未通过，不能标记完整',rollback='确认无活动任务后恢复baseline-research_engine.py、baseline-report_document.py、baseline-research_jobs.py、baseline-app.js并重启服务，保留历史任务与新模块文件；不改语料库',attribution_limit='同题同模型同资料库的单次观察；新增台账调用、3000Token草稿180秒上限和上下文裁剪，不作等预算因果归因'))
else:
 key=(out/'candidate-job-id.txt').read_text().strip();response=requests.get(base+'/api/research/jobs/'+key,timeout=20);response.raise_for_status();job=response.json()
dump(out/'candidate-job.json',job)
if job.get('result'):(out/'candidate-report.md').write_text(job['result']['report'],encoding='utf-8')
e=(job.get('events') or [{}])[-1]
print(json.dumps(dict(id=job['id'],status=job['status'],stage=e.get('stage'),detail=e.get('detail'),elapsed=e.get('elapsed'),error=job.get('error')),ensure_ascii=False))
