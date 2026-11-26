import json
from pathlib import Path
from corpus import connection
from vectors import chunks
from research_engine import bounded_context
from notice_rules import is_notice_law
p=Path('runs/report-v3');j=json.loads((p/'candidate-job.json').read_text(encoding='utf-8'));plan=j['checkpoint']['plan']
ids={}
for e in j['events']:
 for key in e.get('source_ids',[]):
  ids.setdefault(key,[])
  ids[key]=list(dict.fromkeys(ids[key]+[i['id'] for i in plan['issues'] if i['query']==e.get('query')]))
with connection() as db:docs=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents')]
ds={part['id']:dict(d,id=part['id'],text=part['text'],retrieval_issues=ids[part['id']],fragment=dict(index=part['index'],start=part['start'],end=part['end'],source_length=len(d['text']))) for d in docs for part in chunks(d) if part['id'] in ids}
coverage=next((e['coverage'] for e in reversed(j['events']) if e.get('coverage')),[])
for issue in plan['issues']:
 evidence=[ds[key] for key in ids if ds[key]['doc_type']=='law' or not ids[key] or issue['id'] in ids[key]]
 preferred=[d['id'] for d in evidence if is_notice_law(d) or issue['id'] in d.get('retrieval_issues',[])]
 required={ref['source_id'] for row in coverage if row['issue_id']==issue['id'] for ref in row.get('references',[])}
 if issue.get('requires_notice'):required.update(d['id'] for d in evidence if is_notice_law(d))
 context=bounded_context(evidence,preferred=preferred,required=required)
 print(json.dumps(dict(issue=issue['id'],source_ids=[d['id'] for d in context],chars=len(json.dumps(context,ensure_ascii=False))),ensure_ascii=False))
