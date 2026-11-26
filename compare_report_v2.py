"""Inspect the actual completed same-question run; never overwrite its history."""
import json,hashlib
from pathlib import Path
from collections import Counter
from official_bulk import dump
from research_engine import quote_check,normalize
ROOT=Path(__file__).parent;OUT=ROOT/'runs/report-v2'
def main():
 old=json.loads((OUT/'baseline-job.json').read_text(encoding='utf-8'));job=json.loads((OUT/'candidate-job.json').read_text(encoding='utf-8'))
 assert job['status']=='completed',job.get('error') or job['status']
 r=job['result'];before=old['result'];assert job['question']==old['question']==r['question']
 assert r['mode']==before['mode'];assert r['report_version']=='legal-report-v2'
 sources={d['id']:d for d in r['evidence']};checks=r['verification']['checks'];accepted=[c for c in checks if c['status']=='supported']
 assert accepted and all(not quote_check(ref,sources) for c in accepted for ref in c['references'])
 assert not any(sources[ref['source_id']].get('reference_status')=='not_reference' for c in accepted for ref in c['references'])
 assert all(c['statement'] in r['report'] for c in accepted)
 for c in checks:
  if c['status']!='supported' and c['statement'] not in {x['statement'] for x in accepted}:assert c['statement'] not in r['report']
 for f in r.get('facts',[]):
  if f['status']=='provided':assert normalize(f['text']) in normalize(r['question'])
 result=dict(baseline_job='f36800c83a2146f2a1a215a2f9b2e1a0',candidate_job=job['id'],question_identical=True,model_identical=True,mode=r['mode'],
  baseline=dict(elapsed=before['elapsed'],accepted=before['verification']['accepted'],report_chars=len(before['report']),budget=before['budget']),
  candidate=dict(elapsed=r['elapsed'],outcome=r['outcome'],accepted=len(accepted),rejected=len(checks)-len(accepted),role_counts=dict(Counter(c.get('role','conclusion') for c in accepted)),facts=len(r.get('facts',[])),report_chars=len(r['report']),quality=r['report_quality'],budget=r['budget'],supplement_rounds=r['supplement_rounds']),
  boundaries=dict(original_fact_quotes_match=True,published_quotes_match=True,excluded_sources_leaked=0,rejected_statements_published=0),
  scope='同题单次真实运行。正文长度仅为描述值，不作准确率；预算扩大、模型随机性及检索变化使改进不能单独归因某一提示词。')
 result['failed_attempts']=[dict(job_id=p['id'],status=p['status'],error=p.get('error'),error_details=p.get('error_details')) for path in sorted(OUT.glob('failed-attempt-*-job.json')) for p in [json.loads(path.read_text(encoding='utf-8'))]]
 result['recovery']=r.get('recovery');result['candidate']['budget_scope']=r.get('budget_scope','完整任务预算')
 dump(OUT/'comparison.json',result)
 dump(OUT/'candidate-hashes.json',{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ('research_engine.py','report_document.py','server.py','app.js')})
 lines=['# 专项法律报告第二版：同题真实运行对照','',f"原任务：{result['baseline_job']}；新任务：{job['id']}。问题逐字一致，语言模型均为{r['mode']}。",'',
 '| 观察项 | 历史报告 | 本次实际报告 |','| --- | --- | --- |',
 f"| 耗时 | {before['elapsed']}秒 | {r['elapsed']}秒（含故障诊断与恢复等待，不是纯模型耗时） |",f"| 通过核验的单元 | {before['verification']['accepted']}条简短主张 | {len(accepted)}项分类型分析 |",
 f"| 报告字符数 | {len(before['report'])} | {len(r['report'])}（仅描述篇幅，不作为质量评分） |",f"| 补检索轮数 | {before.get('supplement_rounds',0)} | {r['supplement_rounds']} |",'',
 '## 本次内容与验证','',json.dumps(result['candidate']['role_counts'],ensure_ascii=False), '',
 f"结构完整性：{'通过' if r['report_quality']['passed'] else '仍有缺口'}。{r['report_quality']['case_status']}。",'',
 '所有公开的事实适用、支持理由、反方论证、比较和建议均来自通过检查的分析单元；摘要复用已通过的结论。程序复查确认：引用逐字匹配，题设陈述逐字可追溯，没有引用默认排除的失效或旧版本，未通过单元没有进入正式正文。', '',
 '报告正文见[candidate-report.md](candidate-report.md)，原始任务、模型检查、补检索与拒绝记录见[candidate-job.json](candidate-job.json)。主张检查中仍含模型判断，并不能证明法律结论全部正确。','',
 '## 首轮失败及修正','',
 '前两次候选分别在120秒、240秒长草稿请求上限内超时。第三次在证据评估阶段收到HTTP 400，提供方仅返回模型名，无可定位原因；最小请求和缩小证据的诊断请求均成功，但不能据此证明400的根因。三次记录保留于failed-attempt-*-job.json。现将正文按争点生成、核验按每6项分批，每批2600输出Token、至多3路并发；规范评估只读法条，正文案例按争点选择，核验保留全部规范和本批引用的案例。另一次诊断运行暴露了621条检验期限误用于催告期限且模型核验漏判，以及一年解除权期限未交代适用前提的问题，已增加程序检查；诊断记录另存pre-scope-guard-job.json。本次修订后从拆题重新运行，并非手工改写诊断报告。', '',
 '## 对照边界','',
 '辅助脚本一次通过临时进程启动后台任务，在Python退出时触发嵌套执行器不可再调度的异常，记录为failed-attempt-04-job.json；独立最小复现见diagnose_nested_executor.py。该辅助方式已移除，本次最终任务由常驻HTTP服务启动。诊断运行在600秒总上限附近的请求超时会丢失已核验结果，现已增加到期时仅保留此前核验通过内容的处理及回归测试。', '',
 '这是一次同题观察，不是普遍准确率评测。时间上限由480秒提高到900秒，请求输出总额度由16000提高到48000，累计输入字符由180000提高到600000；最多24次模型调用、9次检索、两轮补检索。模型条件相同，预算及生成结构改变，不作等预算因果归因。旧报告及数据库任务不改写。','',
 '131项回归测试及独立浏览器渲染检查通过。真实任务页面另行检查正文、来源跳转与导出；其结果保存在同目录。回退文件与触发条件见change.json。', '',
 '## 故障续跑与统计边界','',
 '最终任务从repair-parent-job.json所记同题完整研究的修订检查点继续，并非从零开始的一次成功调用。父任务已经实际运行拆题、混合检索、证据评估、首轮18项核验及补检索，修订请求HTTP 400失败。恢复阶段复用了其记录的22条命中，对片段与引用逐字复核后，仅重新生成被拒绝或新程序规则拦截的类型并调用真实模型核验；父任务不改写。失败父任务未保存预算快照，因此最终budget只表示恢复阶段，不知道准确累计调用及Token额度。事实清单未持久化，恢复结果facts为空，未伪造已查验材料；事实适用仍保留在逐争点正文。细节见recovery字段。', '',
 '## 需要人工阅读判断的部分','',
 '应重点复查法定要件的拆分、损失与违约金的关系、对方合理抗辩的完整性、案例差异是否决定性，以及建议是否与现有证据相称。上述结构和来源检查不能代替专业复核。','']
 (OUT/'comparison.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps(result['candidate'],ensure_ascii=False))
if __name__=='__main__':main()
