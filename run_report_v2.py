"""Run the same saved late-delivery question through the real local job API."""
import json,sys,hashlib
from pathlib import Path
import requests
from official_bulk import dump
ROOT=Path(__file__).parent;OUT=ROOT/'runs/report-v2'
base='http://127.0.0.1:8765'
def main(action):
 baseline=json.loads((OUT/'baseline-job.json').read_text(encoding='utf-8'))
 if action=='start':
  if (OUT/'candidate-job-id.txt').exists():raise ValueError('Candidate already recorded; poll it rather than duplicate the job')
  h=requests.get(base+'/api/health',timeout=20);h.raise_for_status();health=h.json()
  assert health['report_version']=='legal-report-v2' and health['vectors']['ready']
  r=requests.post(base+'/api/research/jobs',json=dict(question=baseline['question']),timeout=20);r.raise_for_status();job=r.json()
  (OUT/'candidate-job-id.txt').write_text(job['id'],encoding='utf-8')
  dump(OUT/'change.json',dict(change_id='report-v2-20261113',authorization='用户要求按专业标准改造报告生成并用相同逾期交付问题完整重跑',baseline_job='f36800c83a2146f2a1a215a2f9b2e1a0',candidate_job=job['id'],question=baseline['question'],hypothesis='逐争点的事实适用、正反论证、类案比较及建议可以全部置于主张验证链中，结构缺失不再报告为完整研究',health=health,corpus_sha256=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))['corpus_sha256'],baseline_hashes={n:hashlib.sha256((OUT/('baseline-'+n)).read_bytes()).hexdigest() for n in ('research_engine.py','app.js','server.py')},attribution_limit='同一问题与模型，增加结构化输出及调用预算；一次运行，不能据此证明普遍准确率提升',rollback='停用研究服务且确认无活动任务后恢复baseline-research_engine.py、baseline-app.js与baseline-server.py并重启；不改写已完成历史任务'))
 else:
  key=(OUT/'candidate-job-id.txt').read_text(encoding='utf-8').strip()
  r=requests.get(base+'/api/research/jobs/'+key,timeout=20);r.raise_for_status();job=r.json()
  dump(OUT/'candidate-job.json',job)
  if job.get('result'):(OUT/'candidate-report.md').write_text(job['result']['report'],encoding='utf-8')
 events=job.get('events',[])
 print(json.dumps(dict(id=job['id'],status=job['status'],last_event=events[-1] if events else None,error=job.get('error')),ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
