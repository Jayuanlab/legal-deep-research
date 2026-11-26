"""Compact, read-only inspection of the recorded candidate output."""
import json
from pathlib import Path
p=Path(__file__).parent/'runs/report-v2/candidate-job.json'
j=json.loads(p.read_text(encoding='utf-8'));r=j.get('result')
print('STATUS',j['status'])
if r:
 print('QUALITY',json.dumps(r['report_quality'],ensure_ascii=False))
 print('BUDGET',json.dumps(r['budget'],ensure_ascii=False))
 print('CHECKS')
 for c in r['verification']['checks']:
  print(c['claim_id'],c['issue_id'],c.get('role'),c['status'],c.get('fact_status'),c['reason'],c.get('fact_reason'))
 print('ASSESSMENT',json.dumps(r['assessment'],ensure_ascii=False))
 print('EVENTS')
 for e in r['events']:print(e['elapsed'],e['stage_key'],e['state'],e['detail'])
 print('REPORT\n'+r['report'])
