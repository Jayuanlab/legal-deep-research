import json,re
from pathlib import Path
from collections import Counter
from official_bulk import dump
from research_engine import quote_check
from notice_rules import notice_errors
from report_ledger import ledger_quality
root=Path(__file__).parent;out=root/'runs/report-v3'
job=json.loads((out/'reviewed-job.json').read_text(encoding='utf-8'));old=json.loads((out/'baseline-job.json').read_text(encoding='utf-8'))
research_root=json.loads((out/'root-job.json').read_text(encoding='utf-8'))
assert job['status']=='completed',job.get('error')
r=job['result'];before=old['result'];assert r['question']==old['question'] and r['mode']==before['mode']
assert not research_root.get('parent_job') and job['parent_job']==research_root['id']
assert r['recovery']['root_started_fresh'] and not r['recovery']['used_v2_outputs']
assert r['report_version']=='legal-report-v3'
sources={d['id']:d for d in r['evidence']};accepted=[c for c in r['verification']['checks'] if c['status']=='supported']
assert accepted and all(not quote_check(ref,sources) for c in accepted for ref in c['references'])
assert all(c['statement'] in r['report'] for c in accepted)
assert all(d.get('reference_status')!='not_reference' for c in accepted for ref in c['references'] for d in [sources[ref['source_id']]])
for c in r['verification']['checks']:
 if c['status']!='supported' and c['statement'] not in {x['statement'] for x in accepted}:assert c['statement'] not in r['report']
notices=[c for c in accepted if c.get('role')=='notice']
case_ids={sources[c['case_source_id']].get('parent_id',c['case_source_id']) for c in accepted if c.get('role')=='case_comparison'}
for c in notices:assert not notice_errors(c,sources)
ledger=ledger_quality(r,r['research_plan'],r['verification'])
assert notices and ledger['passed']
checkpoint=job.get('checkpoint',{}).get('document',{})
assert checkpoint.get('facts')==r['facts'] and checkpoint.get('materials')==r['materials']
for f in r['facts']:
 if f['status']=='provided':
  assert re.sub(r'\s+','',f['text']) in re.sub(r'\s+','',r['question'])
  assert not re.search('能否|如何|[?？]',f['text']),'A legal question is not a confirmed fact'
notice_issues={i['id'] for i in r['research_plan']['issues'] if i.get('requires_notice')}
elements={m['element'] for m in r['materials'] if m['issue_id'] in notice_issues}
result=dict(baseline_job=old['id'],candidate_job=job['id'],fresh_run=False,fresh_root=True,root_job=research_root['id'],root_status=research_root['status'],recovered_from_current_run_checkpoint=True,question_identical=True,model_identical=True,mode=r['mode'],
 baseline=dict(accepted=before['verification']['accepted'],facts=len(before.get('facts',[])),materials=len(before.get('materials',[])),notice_units=sum(c.get('role')=='notice' and c['status']=='supported' for c in before['verification']['checks']),elapsed=before['elapsed'],elapsed_scope='上一版包含故障续跑和诊断等待'),
 candidate=dict(outcome=r['outcome'],accepted=len(accepted),rejected=len(r['verification']['checks'])-len(accepted),role_counts=dict(Counter(c.get('role') for c in accepted)),facts=len(r['facts']),provided_facts=sum(f['status']=='provided' for f in r['facts']),materials=len(r['materials']),notice_units=len(notices),ledger=ledger,notice_material_elements=sorted(elements),notice_material_coverage={'cure','notice_arrival','court_service'}<=elements,elapsed=r['elapsed'],supplement_rounds=r['supplement_rounds'],budget=r['budget'],quality=r['report_quality']),
 verification=dict(published_quotes_match=True,published_rejected_units=0,excluded_sources=0,checkpoint_ledger_preserved=True),
 scope='同题同模型、资料库不变：本轮根任务从头运行，修订失败后使用本轮检查点补完。未用上一版模型输出；不是单次无故障完整成功，不作等预算速度或法律准确率归因。')
dump(out/'comparison.json',result)
result['candidate'].update(distinct_cases=len(case_ids),budget_scope=r.get('budget_scope'),manual_review_status='needs_revision',professional_report_ready=False)
dump(out/'comparison.json',result)
lines=['# 解除通知与材料台账：同题实跑对照','',f"旧任务：{old['id']}；本轮根任务：{research_root['id']}；检查点恢复任务：{job['id']}。根任务从头执行，恢复仅用本轮检查点，不复用上一版结论。原始失败根任务保持原样。",'',
 '| 观察项 | 上一版 | 本次 |','| --- | --- | --- |',f"| 通过的分析单元 | {result['baseline']['accepted']} | {len(accepted)} |",f"| 独立通知路径分析 | 0 | {len(notices)} |",f"| 事实记录 | {result['baseline']['facts']} | {len(r['facts'])}（题设摘录{result['candidate']['provided_facts']}） |",f"| 材料核对项 | 0 | {len(r['materials'])} |",f"| 台账与已核验分析关联 | 无 | {'通过' if ledger['passed'] else '仍有缺口'} |",f"| 通知相关材料覆盖 | 未建立 | {', '.join(sorted(elements))} |",'',
 '## 真实执行与边界','',f"本次模型{r['mode']}；墙钟时间{r['elapsed']}秒（含故障与诊断等待），本轮根任务补检索{r['supplement_rounds']}轮。budget只记恢复阶段{r['budget']['model_calls']}次逻辑调用；根任务核验前快照另存，失败修订的累计预算未完整保存，不能将恢复调用数冒充全程调用数。Token额度不是计费实耗。",'',
 f"结果状态：{r['outcome']}；分析结构检查：{r['report_quality']['passed']}；材料台账检查：{ledger['passed']}。这些检查不能证明全部法律结论正确。",'',
 '程序复查确认引用连续匹配、拒绝段落不进入正文、已排除来源未泄漏；通知段落另行检查第565条及三条路径，事实与材料清单在检查点中保存，修订不会重建为空。', '',
 '首个候选在材料台账解析时失败，未产生报告，记录保留在attempt-01-job.json。之后改进问句识别并增加一次有界格式修复。第二次候选在检查点暴露必备材料遗漏及通知关联不准确，主动取消。第三次诊断发现上下文裁剪可能挤出新补到的关键规范，主动取消，现优先保留覆盖引用及第565条。第四次候选在正文生成结束时被旧事实字段校验拒绝，现由独立校验的台账统一管理事实，正文中不再生成或发布重复事实清单。各次记录见attempt-01至04-job.json及相应回执。最终候选重新从拆题开始运行，不把这些诊断隐去或包装成成功。', '',
 '第五次候选因嵌入式“是否”问句缺少句尾问号被误拒，原始诊断记录保存于attempt-05-job.json；已加入回归。最终根任务真实运行拆题、台账、混合检索、两轮补检索、生成19项及逐段核验，修订时因多返回非目标类型失败，完整记录见root-job.json。恢复阶段过滤未请求段落，并拦住原通知单元遗漏实际未履行条件的漏判，重新生成并核验三处目标类型。', '',
 '## 复读后的最终判断','',
 '自动流程状态complete不代表专业终稿合格。复读仍发现摘要遗漏确认条件、个别引用不直接支持判断，以及支持段先认定本案未实施替代交易等问题。两组类案比较实际引用同一个T20109案。专业报告准备状态为needs_revision，不能用自动20项通过掩盖这些漏判。', '',
 '建议先看[带审读提示的实跑报告](report-with-review-notes.md)及[具体复读记录](manual-review.md)。原始模型报告见[reviewed-report.md](reviewed-report.md)，实际导出见[reviewed-export.md](reviewed-export.md)，均保留原文便于复核。','']
(out/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(result['candidate'],ensure_ascii=False))
