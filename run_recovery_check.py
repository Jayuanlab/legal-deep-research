"""Retry the user's failed question through the real local research API."""
import argparse
import json
import time
import urllib.request
from pathlib import Path
from research_jobs import get_job

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-job',default='4d99d17b208c44e99a542a1fad596c07');args=parser.parse_args()
    source=get_job(args.source_job)
    if not source:raise ValueError('Source job missing')
    base='http://127.0.0.1:8765';out=Path(__file__).parent/'runs';out.mkdir(exist_ok=True)
    req=urllib.request.Request(base+'/api/research/jobs',data=json.dumps(dict(question=source['question']),ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
    job=json.load(urllib.request.urlopen(req,timeout=15));key=job['id'];print('JOB '+key,flush=True)
    seen=0;start=time.monotonic()
    while True:
        job=json.load(urllib.request.urlopen(base+'/api/research/jobs/'+key,timeout=15))
        for event in job.get('events',[])[seen:]:print(json.dumps({k:v for k,v in event.items() if k!='checks'},ensure_ascii=False),flush=True)
        seen=len(job.get('events',[]))
        if job['status'] not in ('queued','running'):break
        if time.monotonic()-start>600:raise TimeoutError(key)
        time.sleep(2)
    (out/(key+'.json')).write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
    record=dict(source_job=source['id'],source_status=source['status'],source_error=source.get('error'),new_job=key,status=job['status'],question_identical=source['question']==job['question'])
    if job['status']=='completed':
        r=job['result'];record.update(elapsed=r['elapsed'],retrieval_mode=r['retrieval_mode'],retrieval_warning=r['retrieval_warning'],outcome=r['outcome'],accepted=r['verification']['accepted'],invalid=r['verification']['invalid'],budget=r['budget'])
        (out/'network-recovery.md').write_text('# 模型连接故障恢复实测\n\n'+source['question']+'\n\n'+r['report']+'\n\n## 运行统计\n\n```json\n'+json.dumps(record,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    (out/'network-recovery.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False),flush=True)
    if job['status']!='completed':raise RuntimeError(job.get('error','Research failed'))

if __name__=='__main__':main()
