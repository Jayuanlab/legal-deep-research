"""Compare recorded real runs; no model calls or live web access."""
import json
import sys
from pathlib import Path
from research_engine import quote_check

ROOT=Path(__file__).parent/'runs'
OLD='fd82af86e021410fae4c96221c418b3a'
new_id=sys.argv[1] if len(sys.argv)>1 else (ROOT/'latest-complex-job.txt').read_text().strip()
before=json.loads((ROOT/(OLD+'.json')).read_text(encoding='utf-8'))
after=json.loads((ROOT/(new_id+'.json')).read_text(encoding='utf-8'))
assert before['question']==after['question'],'Question changed; not a matched question comparison'
assert after['status']=='completed',after['status']

def summary(job):
    r=job['result'];issue=next(i for i in r['research_plan']['issues'] if '担保' in i['question'] or '保证' in i['question'])
    coverage=next(c for c in r['assessment']['coverage'] if c['issue_id']==issue['id'])
    checks=[c for c in r['verification']['checks'] if c['issue_id']==issue['id']]
    sources={d['id']:d for d in r['evidence']}
    for c in r['verification']['checks']:
        assert all(quote_check(ref,sources) is None for ref in c['references'])
        if c['status']!='supported':assert c['statement'] not in r['report']
    return dict(id=job['id'],elapsed=r['elapsed'],outcome=r['outcome'],rounds=r['supplement_rounds'],
        model_calls=r['budget']['model_calls'],queries=r['budget']['retrieval_queries'],evidence=len(r['evidence']),
        guarantee_issue=issue,coverage=coverage,guarantee_checks=checks,
        article9_retrieved='E26009' in sources,article9_used=any(ref['source_id']=='E26009' for c in checks for ref in c['references']),
        accepted=r['verification']['accepted'],invalid=r['verification']['invalid'])

old=summary(before);new=summary(after)
lines=['# 担保制度解释补库前后实测对比','',
       '原问题逐字一致。本轮仅增加官方司法解释全文及索引，没有修改研究引擎、检索算法、提示词或模型配置；模型输出存在随机性，此为单次前后对比，不能将全部差异归因于扩库。','',
       '| 指标 | 补库前 | 补库后 |','| --- | --- | --- |']
for label,key in [('任务编号','id'),('耗时（秒）','elapsed'),('语言模型调用','model_calls'),('本地查询','queries'),('补检索轮数','rounds'),('证据数量','evidence'),('第9条入选证据','article9_retrieved'),('担保主张引用第9条','article9_used'),('全部通过主张数','accepted'),('整体结果','outcome')]:
    lines.append(f"| {label} | {old[key]} | {new[key]} |")
for title,value in [('补库前担保评估',old),('补库后担保评估',new)]:
    lines+=['','## '+title,'',f"法律覆盖充分：{value['coverage']['sufficient']}",'',value['coverage']['reason']]
    for c in value['guarantee_checks']:
        lines+=['',f"- {c['claim_id']} / {c['status']}：{c['statement']}",f"  验证理由：{c['reason']}",f"  引用：{', '.join(ref['source_id'] for ref in c['references'])}"]
lines+=['','## 来源与边界','',
    '新增法释〔2020〕28号71条，编号E26001—E26071，法条库2314条、指导案例278件、向量分片2911个。官网原始快照及SHA-256随资料保存。',
    '[最高人民法院官方原文](https://www.court.gov.cn/zixun/xiangqing/282721.html)。研究阶段仅查本地库。',
    '法律依据充分不等于题设全部事实已查明，也不保证模型支持性审查正确。应保留“未查验”“未披露”“未根据披露信息订约”之间的区别；规范沿革和个案时间适用仍须核验。',
    f'[补库前完整记录]({OLD}.md)；[补库后完整记录]({new_id}.md)。']
(ROOT/'guarantee-comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(ROOT/'guarantee-comparison.json').write_text(json.dumps(dict(before=old,after=new),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(before=old,after=new),ensure_ascii=False,indent=2))
