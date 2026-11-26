import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import corpus
with corpus.connection() as db:rows=db.execute("SELECT id,payload,updated_at FROM research_jobs WHERE status='completed' ORDER BY updated_at DESC LIMIT 2").fetchall()
for key,raw,at in rows:
 p=json.loads(raw);r=p.get('result',{})
 print('JOB',key,at,'QUESTION',p.get('question'));print(r.get('report','')[:14000])
