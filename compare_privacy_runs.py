"""Summarize matched-question real runs and the independent exact-claim replay."""
import json
import sys
from pathlib import Path
from fact_grounding import language_issues
from research_engine import quote_check

OUT=Path(__file__).parent/'runs'
key=sys.argv[1] if len(sys.argv)>1 else (OUT/'latest-complex-job.txt').read_text().strip()
old=json.loads((OUT/'a90c2c658fb14c779286758dbb3fd0ef.json').read_text(encoding='utf-8'))
new=json.loads((OUT/(key+'.json')).read_text(encoding='utf-8'))
replay=json.loads((OUT/'privacy-replay.json').read_text(encoding='utf-8'))
assert new['status']=='completed' and old['question']==new['question']
r=new['result'];sources={d['id']:d for d in r['evidence']}
issue=next(i for i in r['research_plan']['issues'] if '个人信息' in i['question'])
checks=[c for c in r['verification']['checks'] if c['issue_id']==issue['id']]
for c in r['verification']['checks']:
    assert all(quote_check(ref,sources) is None for ref in c['references'])
    if c['status']=='supported':
        assert c.get('fact_status') in ('grounded','conditional')
        assert not language_issues(c['statement'],new['question'])
    else:assert c['statement'] not in r['report']
assert replay['replayed']['accepted']==0 and replay['budget']['model_calls']==0
assert replay['original']['statement'] not in r['report']
summary=dict(job=key,question_identical=True,elapsed=r['elapsed'],outcome=r['outcome'],budget=r['budget'],
             supplement_rounds=r['supplement_rounds'],accepted=r['verification']['accepted'],privacy_checks=checks,
             replay_status=replay['replayed']['checks'][0]['status'])
lines=['# 个人信息事实越界修正实测','',
       '原始问题逐字一致，资料库及模型配置未变。本轮修改了生成提示、事实语言门禁、独立事实验证字段及核验面板。单次模型运行有随机性，不能承诺所有改写均能识别。','',
       '## 原漏判原样回放','',replay['original']['statement'],'',
       f"旧状态：{replay['original']['status']}；新状态：{replay['replayed']['checks'][0]['status']}。",
       replay['replayed']['checks'][0]['reason'],'',
       '该回放使用原主张、原问题和原证据，不注入新的草稿或模拟模型回复；程序直接拦截，模型调用数0。','',
       '## 新的完整真实运行','',
       f"任务：{key}；耗时：{r['elapsed']}秒；模型调用：{r['budget']['model_calls']}；本地检索：{r['budget']['retrieval_queries']}；补检索：{r['supplement_rounds']}轮；整体状态：{r['outcome']}。",'']
for event in r['events']:
    privacy=[c for c in event.get('checks',[]) if c['issue_id']==issue['id']]
    if privacy:
        lines+=[f"### {event['elapsed']}秒：{event['detail']}",'']
        for c in privacy:
            lines += [f"- {c['claim_id']} / {c['status']}：{c['statement']}",f"  法律验证：{c['reason']}",f"  事实验证：{c.get('fact_status')} / {c.get('fact_reason')}",'']
lines+=['## 修正与验证边界','',
    '事实语言检查只拒绝本次类型的确定断言，不证明行为合法或违法。条件必须出现在支配结论的前提中；句末免责声明、与同意无关的“如果”不算有效条件。',
    '语义验证分别返回法律判断与事实判断。grounded需要能匹配题设的连续引文；conditional表示假设规则；缺字段、未知事实或题设引文不匹配不能发布。短引文存在仍不等于所有前提都被证明。',
    '58项后端测试通过，含旧主张误放行回归、尾部免责声明、无关条件、真实条件、明确未经同意事实、缺失事实检查结果、伪造事实引文以及修订后的发布路径。',
    '语言规则具有覆盖范围和保守拒绝风险，同一模型的法律及事实审查仍可能误判；不能替代人工核实授权、主体权利或法律时际适用。',
    f'[新完整运行记录]({key}.md)；[原漏判回放JSON](privacy-replay.json)；[修正前完整记录](a90c2c658fb14c779286758dbb3fd0ef.md)。']
(OUT/'privacy-fix-comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(OUT/'privacy-fix-comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
