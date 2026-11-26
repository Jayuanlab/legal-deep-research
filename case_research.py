"""Case workbench orchestration: materials, legal research, reject-only review and options."""
import time,re
from models import ModelError,public_config
from matter_store import GOALS,ROLES,profile
from matter_evidence import prepare_context,material_evidence,render_context
from report_review import consistency_review
from report_document import parse_document,quality,render_document
from report_ledger import ledger_quality
from research_engine import research as legal_research,Budget,validate_claims,bounded_context,ResearchStopped,ResearchCancelled

OPTIONS={'performance':('继续取得履行','补交排期、履约能力、继续停工成本及客户能接受的时间'),
 'settlement':('协商变更或和解','可接受交付时间、让步范围、履约保障及协商成本'),
 'termination':('研究解除及后续请求','解除条件、通知到达、价款返还与赔偿/违约金请求关系、替代采购报价'),
 'proceedings':('诉讼或仲裁准备','争议解决条款、举证期限、费用、保全条件及对方偿付资料')}

def strategies(result,context,budget):
 if not any(w in result['question'] for w in ('合同','交付','供应商','设备')):return dict(checks=[],status='本版方案模块先覆盖合同交付争议，未套用到其他案由。')
 issues=result['research_plan']['issues']
 if not issues:return dict(checks=[],status='缺少争点，尚不能比较方案。')
 accepted=[dict(id=c['claim_id'],issue_id=c['issue_id'],statement=c['statement']) for c in result['verification']['checks'] if c['status']=='supported']
 data=budget.ask('针对客户目标比较合同交付争议的可选方案。只输出{"report_version":2,"facts":[],"claims":[{"issue_id":"实际争点ID","role":"strategy|recommendation","option_key":"performance|settlement|termination|proceedings","statement":"80至150字，适用前提、可行性缺口及证据条件","references":[{"source_id":"本次法律或案例编号","quote":"8至40字连续原文"}]}]}。'
  '尽量各方案一项，最多5项。每个公开法律判断均须引用；法条未支持的个案条件不得猜测。成本只说明待核算输入，不造金额、胜率、对方资产或必然回款结论。'
  '客户目标未确认时不得返回recommendation，也不排序；目标明确时最多1项recommendation，必须有条件，说明什么材料或事实变化会改变建议，不能凭目标偏好推定法律可行性。'
  '材料有差异须明确待核，不把材料陈述当已查明。赔偿、违约金及价款返还须区分，不能暗示同一损失全额重复累计。仅用已通过单元和给定本地证据。',
  dict(question=result['question'],issues=issues,client_goal=context.get('goal'),client_role=context.get('client_role'),constraints=context.get('constraints'),options=OPTIONS,accepted=accepted,evidence=bounded_context([d for d in result['evidence'] if d['doc_type'] in ('law','case')])),2400)
 if data.get('claims')==[]:return dict(checks=[],status='当前证据不足以形成通过核验的方案。')
 parsed=parse_document(dict(data,facts=[]),result['question'],result['research_plan'])
 candidates=[]
 for i,c in enumerate(parsed['claims'],1):
  if c['role'] not in ('strategy','recommendation') or c.get('option_key') not in OPTIONS:raise ModelError('方案类型无效。')
  c['id']='S'+str(i)
  if c['role']=='recommendation' and context.get('goal','undecided')=='undecided':
   continue
  if c['role']=='recommendation' and (any(x['role']=='recommendation' for x in candidates) or not re.search('若|如果|前提|条件|待核',c['statement']) or not re.search('改变|调整|重新|变化|不再|否则',c['statement'])):
   continue
  candidates.append(c)
 v=validate_claims(candidates,[d for d in result['evidence'] if d['doc_type'] in ('law','case')],budget,result['question'],result['assessment'])
 return dict(v,status='方案已逐项核验' if v['passed'] else '部分方案未获支持，未进入正文')

def render_options(context,verification):
 lines=['## 处理方案比较','客户目标：'+GOALS[context.get('goal','undecided')]+'；立场：'+ROLES[context.get('client_role','unknown')]]
 if context.get('constraints'):lines+=['客户提供的约束：'+context['constraints']]
 if context.get('goal','undecided')=='undecided':lines+=['客户目标尚未确认，以下只列可研究选项，不作排序或唯一推荐。']
 if context.get('client_role','unknown')=='unknown':lines+=['客户立场尚未确认，方案不能直接视为任一方的行动指令。']
 rows=[c for c in verification.get('checks',[]) if c['status']=='supported']
 for c in rows:
  label,inputs=OPTIONS[c['option_key']]
  lines+=['### '+('有条件的研究建议：' if c['role']=='recommendation' else '')+label,c['statement']+' '+''.join('['+r['source_id']+']' for r in c['references']),
   '待补决策输入：'+inputs+'。']
 if not rows:lines+=[verification.get('status','尚无经过核验的方案，需先补充依据。')]
 lines+=['对外通知、立案、和解或其他法律行为须另行由客户与承办律师确认，本系统未执行这些行为。']
 return lines

def research_case(question,emit=None,cancelled=lambda:False,case_context=None,client_goal=None,budget=None):
 budget=budget or Budget(cancelled=cancelled);extra=[]
 snapshot=case_context or dict(documents=[],name='未绑定案件',**profile(client_goal or {}))
 def event(stage,detail,state='completed'):
  row=dict(stage=stage,stage_key='verify' if stage=='全文复核' else 'draft',detail=detail,state=state,elapsed=round(time.monotonic()-budget.started,2));extra.append(row)
  if emit:emit(row)
 event('案件材料','整理客户目标及本案材料片段。','running')
 context=prepare_context(question,snapshot,budget);budget.matter_context=context
 event('案件材料',f'保留{len(context["observations"])}项可定位的材料陈述、{len(context["differences"])}项待核对差异。')
 result=legal_research(question,emit=emit,cancelled=cancelled,budget=budget)
 ledger=dict(facts=result['facts'],materials=result.get('materials',[]));option_check=dict(checks=[],status='方案比较未完成')
 review_status='not_completed';stop=[]
 try:
  event('方案比较','按客户目标比较可选路径，并逐项核验。','running')
  option_check=strategies(result,context,budget)
  # Keep strategy units in the same consistency pass without losing the legal audit.
  combined=dict(result['verification'],checks=result['verification']['checks']+option_check['checks'])
  event('全文复核','对照台账和材料差异复核全部公开分析。','running')
  reviewed=consistency_review(question,ledger,context,combined,budget)
  ids={c['claim_id'] for c in result['verification']['checks']}
  v=dict(reviewed,checks=[c for c in reviewed['checks'] if c['claim_id'] in ids])
  option_check['checks']=[c for c in reviewed['checks'] if c['claim_id'] not in ids]
  v['accepted']=sum(c['status']=='supported' for c in v['checks']);v['passed']=bool(v['checks']) and all(c['status']=='supported' for c in v['checks'])
  v['cited']=sorted({r['source_id'] for c in v['checks'] if c['status']=='supported' for r in c['references']})
  v['status']='法律分析通过自动检查' if v['passed'] else '部分法律分析未获支持'
  result['verification']=v;review_status='completed'
  event('全文复核',f'一致性复核完成，拦截{len(reviewed["consistency_review"]["flags"])}项。')
 except ResearchCancelled:raise
 except (ModelError,ResearchStopped,ValueError) as error:
  stop.append('新增审阅环节未完成：'+str(error));event('全文复核',stop[-1],'limited')
 v=result['verification'];q=quality(result['research_plan'],v,result['evidence']);q['ledger']=ledger_quality(ledger,result['research_plan'],v)
 q['strategy_units']=sum(c['status']=='supported' for c in option_check['checks']);q['consistency_review']=review_status
 q['passed']=q['passed'] and q['ledger']['passed'] and q['strategy_units']>0 and review_status=='completed'
 outcome='complete' if result['assessment']['sufficient'] and v['passed'] and q['passed'] and not stop else 'limited'
 stop_reason='；'.join(stop) or ('自动流程完成，结论仍须律师复核。' if outcome=='complete' else '保留有限研究结果；未通过的判断和方案不进入正文。')
 doc=dict(ledger,claims=[],case_context=context)
 public_check=dict(v,checks=v['checks']+[c for c in option_check['checks'] if c['status']=='supported'])
 report=render_document(result['research_plan'],result['assessment'],public_check,doc,result['evidence'],question,stop_reason)
 insert='\n\n'.join(render_context(context))+'\n\n'
 report=report.replace('## 三、逐争点分析',insert+'## 三、逐争点分析',1)
 report+='\n\n'+'\n\n'.join(render_options(context,option_check))
 final_evidence=result['evidence']+material_evidence(context)
 result.update(report_version='legal-workbench-v4',report=report,case_context=context,strategy_verification=option_check,report_quality=q,outcome=outcome,review_status='automated_checks_passed_pending_lawyer' if outcome=='complete' else 'needs_revision',stop_reason=stop_reason,evidence=final_evidence,budget=budget.snapshot(),elapsed=round(time.monotonic()-budget.started,2),events=sorted(result['events']+extra,key=lambda e:e.get('elapsed',0)))
 return result
