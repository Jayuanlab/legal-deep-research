import json,hashlib,shutil,re
from pathlib import Path
import requests
from official_bulk import dump
root=Path(__file__).parent;out=root/'runs/report-v3'
job=json.loads((out/'reviewed-job.json').read_text(encoding='utf-8'));r=job['result']
research_root=json.loads((out/'root-job.json').read_text(encoding='utf-8'))
comparison=json.loads((out/'comparison.json').read_text(encoding='utf-8'))
ui=json.loads((out/'live-ui-validation.json').read_text(encoding='utf-8'))
assert job['status']=='completed' and not research_root.get('parent_job') and comparison['fresh_root']
assert comparison['candidate']['notice_units']>0 and comparison['candidate']['ledger']['passed']
assert comparison['candidate']['notice_material_coverage']
assert ui['passed'] and ui['job_id']==job['id']
log=(root/'report-v3-tests.log').read_text(encoding='utf-8');assert log.strip().endswith('OK')
count=int(re.search(r'Ran (\d+) tests',log).group(1))
change=json.loads((out/'change.json').read_text(encoding='utf-8'))
hashes={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in change['candidate_hashes']}
root_hashes={n:hashlib.sha256((out/('root-runtime-'+n)).read_bytes()).hexdigest() for n in change['candidate_hashes']}
assert root_hashes==change['candidate_hashes'],'Saved root runtime differs from recorded launch'
health=requests.get('http://127.0.0.1:8765/api/health',timeout=30).json();assert health['report_version']=='legal-report-v3'
diagnostics=[]
for p in sorted(out.glob('attempt-*-job.json')):
 j=json.loads(p.read_text(encoding='utf-8'));diagnostics.append(dict(id=j['id'],status=j['status'],error=j.get('error'),artifact=p.name))
change.update(revision_hashes=hashes,delivery_job=job['id'],root_status=research_root['status'],rollout='已加载含漏判防护的最终代码；根任务从头执行、修订失败后由本轮检查点补完，历史不改写',evaluation=dict(job_id=job['id'],fresh_run=False,fresh_root=True,recovered=True,outcome=r['outcome'],notice_units=comparison['candidate']['notice_units'],facts=len(r['facts']),materials=len(r['materials']),accepted=r['verification']['accepted'],regression_tests=count,ui_and_export=True,limitations='单题观察；模型审查不等于法律结论全部正确，效力与个案原件仍待核实'),diagnostic_attempts=diagnostics)
change['evaluation'].update(manual_review_status='needs_revision',professional_report_ready=False,distinct_cases=comparison['candidate']['distinct_cases'])
dump(out/'change.json',change)
dump(out/'acceptance-result.json',dict(job_id=job['id'],core_feature_checks_passed=True,professional_report_ready=False,manual_review_status='needs_revision',outcome=r['outcome'],comparison='comparison.json',ui='live-ui-validation.json',tests=count,notice_units=comparison['candidate']['notice_units'],ledger=comparison['candidate']['ledger'],fresh_run=False,fresh_root=True,recovered=True,root_status=research_root['status'],history_preserved=True,diagnostic_attempts=diagnostics))
for name in change['candidate_hashes']:shutil.copyfile(root/name,out/('reviewed-runtime-'+name))
for name in ('reviewed-report.md','reviewed-export.md','comparison.md','manual-review.md'):
 text=(out/name).read_text(encoding='utf-8');assert '\ufffd' not in text and '???' not in text,name
print(json.dumps(dict(job_id=job['id'],outcome=r['outcome'],accepted=r['verification']['accepted'],facts=len(r['facts']),materials=len(r['materials']),notice_units=comparison['candidate']['notice_units'],tests=count,diagnostic_attempts=len(diagnostics)),ensure_ascii=False))
