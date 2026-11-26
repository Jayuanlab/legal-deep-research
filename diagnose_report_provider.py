"""Read safe provider error fields; never print credentials or request bodies."""
import json,re,urllib.request,urllib.error,uuid,sys
from models import config
c=config()[0]
if len(sys.argv)>1 and sys.argv[1]=='assessment':
 from pathlib import Path
 import research_engine as engine
 from corpus import connection
 from vectors import chunks
 job=json.loads(Path('runs/report-v2/candidate-job.json').read_text(encoding='utf-8'))
 issues=next(e['issues'] for e in job['events'] if 'issues' in e)
 ids=list(dict.fromkeys(i for e in job['events'] for i in e.get('source_ids',[])))
 with connection() as db:docs=[json.loads(row[0]) for row in db.execute('SELECT payload FROM documents')]
 evidence=[]
 for doc in docs:
  for part in chunks(doc):
   if part['id'] in ids:evidence.append(dict(doc,id=part['id'],text=part['text']))
 print(json.dumps(dict(evidence=len(evidence),packed_chars=len(json.dumps(engine.packed(evidence),ensure_ascii=False)),ids=ids)),flush=True)
 if len(sys.argv)>2:
  evidence=evidence[:int(sys.argv[2])]
 original=urllib.request.OpenerDirector.open
 def observed(self,*args,**kwargs):
  try:return original(self,*args,**kwargs)
  except urllib.error.HTTPError as error:
   raw=error.read(20000).decode('utf-8',errors='replace').replace(c['key'],'[redacted]')
   print(json.dumps(dict(status=error.code,safe_error=re.sub(r'https?://[^\s"<>]+','[url]',raw)[:1200]),ensure_ascii=False),flush=True)
   raise
 urllib.request.OpenerDirector.open=observed
 try:
  result=engine.assess(job['question'],dict(issues=issues,missing_facts=[]),evidence,engine.Budget())
  print(json.dumps(dict(status='ok',sufficient=result['sufficient'],evidence=len(evidence)),ensure_ascii=False))
 except engine.ModelError as error:print(str(error))
 sys.exit(0)
payload=dict(model=c['model'],system='Return only JSON.',messages=[dict(role='user',content='Return {"ok":true}')],max_tokens=200)
request=urllib.request.Request(c['base']+'/v1/messages',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'legal-research-demo/0.2','x-api-key':c['key'],'Authorization':'Bearer '+c['key'],'anthropic-version':'2023-06-01','x-opencode-session':'legal-'+str(uuid.uuid4())})
try:
 with urllib.request.urlopen(request,timeout=45) as response:
  data=json.load(response)
 print(json.dumps(dict(status='ok',stop_reason=data.get('stop_reason'),content_types=[p.get('type') for p in data.get('content',[])])))
except urllib.error.HTTPError as error:
 raw=error.read(20000).decode('utf-8',errors='replace');error.close()
 safe=raw.replace(c['key'],'[redacted]')
 safe=re.sub(r'(?:https?://)[^\s"<>]+','[url]',safe)
 print(json.dumps(dict(status=error.code,error=safe[:1200]),ensure_ascii=False))
