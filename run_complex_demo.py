"""Run a real end-to-end research job through the local HTTP API."""
import json
import time
import urllib.request
from pathlib import Path

QUESTION='''甲公司向乙公司采购人事管理SaaS系统，合同价120万元，已付60万元，约定2025年9月30日上线。乙公司延期三个月，经甲公司书面催告并给予30天期限仍无法上线。甲另找供应商花费150万元采购同等服务，准备解除原合同。乙公司的母公司丙（上市公司）出具连带责任保证函，由法定代表人签字并盖公章，但甲未查验董事会或股东会决议，也未查验公开披露信息。乙在试运行中把甲提供的员工身份证、银行账户及健康信息交给未在合同中披露的丁公司处理，且丁拟用于训练其通用模型。请分别研究四项请求：1.甲是否可以解除合同，需履行什么通知程序；2.解除后60万元预付款与替代采购增加的30万元应如何处理，哪些损失证明仍不足；3.甲能否要求丙承担保证责任，上市公司未披露担保对效力和甲的审查义务有什么影响；4.乙转委托及丁改变处理目的应满足哪些个人信息保护要求，甲现在应要求采取什么措施。请区分本地已收录依据能够支持的判断和仍缺少专门司法解释、事实证据的部分。'''
ROOT=Path(__file__).parent
OUT=ROOT/'runs';OUT.mkdir(exist_ok=True)
BASE='http://127.0.0.1:8765'
request=urllib.request.Request(BASE+'/api/research/jobs',data=json.dumps({'question':QUESTION},ensure_ascii=False).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
job=json.load(urllib.request.urlopen(request,timeout=20))
key=job['id'];print('JOB '+key,flush=True)
(OUT/'latest-complex-job.txt').write_text(key,encoding='utf-8')
seen=0;started=time.monotonic()
while True:
    job=json.load(urllib.request.urlopen(BASE+'/api/research/jobs/'+key,timeout=20))
    events=job.get('events',[])
    for event in events[seen:]:print(json.dumps(event,ensure_ascii=False),flush=True)
    seen=len(events)
    if job['status'] not in ('queued','running'):break
    if time.monotonic()-started>600:raise TimeoutError('Local job exceeded monitor timeout: '+key)
    time.sleep(3)
(OUT/(key+'.json')).write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding='utf-8')
if job['status']!='completed':raise RuntimeError(job.get('error',job['status']))
result=job['result']
audit=['## 实际问题拆解']+[f"- {i['id']}：{i['question']}\n  检索词：{i['query']}" for i in result['research_plan']['issues']]
audit+=['## 实际检索与评估记录']+[f"- {e['elapsed']}秒 / {e['stage']} / {e['state']}：{e['detail']}" for e in result['events'] if e['stage_key'] in ('retrieve','supplement','assess') and e['state']!='running']
audit+=['## 历次引用验证']
for event in result['events']:
    if event.get('checks'):
        audit+=[f"### {event['elapsed']}秒：{event['detail']}"]
        for check in event['checks']:
            audit+=[f"- {check['claim_id']} / {check['status']}：{check['statement']}\n  验证理由：{check['reason']}"]
(OUT/(key+'.md')).write_text('# 复杂法律问题真实运行记录\n\n'+QUESTION+'\n\n'+'\n\n'.join(audit)+'\n\n'+result['report']+'\n\n## 执行统计\n\n```json\n'+json.dumps({k:result.get(k) for k in ('outcome','elapsed','supplement_rounds','stop_reason','budget','verification')},ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
print('RESULT '+json.dumps({k:result.get(k) for k in ('outcome','elapsed','supplement_rounds','stop_reason','budget')},ensure_ascii=False),flush=True)
print('SAVED '+str(OUT/(key+'.json')),flush=True)
