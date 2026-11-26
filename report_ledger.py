"""Fact/material requests, separate from verified legal propositions."""
import re
from models import ModelError
from fact_grounding import language_issues

ELEMENTS={'obligation':'主要交付义务与履行期限','cure':'催告到达、合理期限及届满后履行情况',
 'termination_period':'解除权行使期限及特别约定','notice_arrival':'解除通知的途径、内容与到达时点',
 'notice_condition':'附期限解除通知的期限及届满后履行情况','court_service':'起诉状或仲裁申请书副本的送达时点',
 'loss':'损失项目、金额、因果关系与计算资料','mitigation':'替代交易、减损措施及获益情况',
 'penalty':'违约金约定、损失基数及履约背景','other':'其他待核实事实'}
ALLOWED_ROLES={'conclusion','rule','application','supporting','counterargument','case_comparison','action','notice'}
NOTICE_MATERIALS={
 'obligation':('合同原文及补充协议','合同对交付内容、履行期限及主要义务如何约定？',['application']),
 'termination_period':('解除权特别期限约定及相关时间记录','是否存在解除权特别行使期限，何时知悉解除事由、是否收到相对方催告？',['action','application']),
 'cure':('催告函、到达及后续履行记录','催告何时到达、给予何种宽限期，期限届满后是否仍未履行？',['application']),
 'notice_arrival':('解除通知及到达凭证','是否发出解除通知，其内容、途径、约定地址及实际到达时间为何？',['notice']),
 'notice_condition':('附期限解除通知及期满履行记录','通知是否载明一定期限内不履行则解除，期限何时届满及届满时履行情况为何？',['notice']),
 'court_service':('诉讼或仲裁材料及副本送达记录','是否选择直接起诉或申请仲裁、主张是否获确认，相关副本何时送达对方？',['notice'])}

def complete_requests(ledger,plan):
 """Complete a document-request checklist, never facts or legal conclusions."""
 rows=[dict(m) for m in ledger.get('materials',[])];facts=list(ledger.get('facts',[]))
 for issue in plan['issues']:
  if not issue.get('requires_notice'):continue
  for element,(name,question,roles) in NOTICE_MATERIALS.items():
   found=[m for m in rows if m['issue_id']==issue['id'] and m['element']==element]
   if found:
    if element in ('notice_arrival','notice_condition','court_service'):
     for m in found:m['claim_roles']=['notice']
   else:rows.append(dict(issue_id=issue['id'],element=element,name=name,question=question,claim_roles=roles,status='not_submitted',origin='system_checklist'))
 for n,m in enumerate(rows,1):m['id']='M'+str(n)
 return dict(facts=facts,materials=rows)

def parse_ledger(data,question,plan):
 facts=data.get('facts',[]);materials=data.get('materials',[])
 if not isinstance(facts,list) or len(facts)>12 or not isinstance(materials,list) or len(materials)>12:raise ModelError('事实材料台账数量无效。')
 cleaned=[];issues={i['id'] for i in plan['issues']}
 for f in facts:
  if not isinstance(f,dict) or f.get('status') not in ('provided','unknown'):raise ModelError('事实台账不得冒充已核验事实。')
  text=f.get('text','')
  if not isinstance(text,str) or not 4<=len(text)<=500:raise ModelError('事实台账文字无效。')
  if f['status']=='provided' and re.sub(r'\s+','',text) not in re.sub(r'\s+','',question):raise ModelError('台账题设事实无法逐字匹配。')
  if f['status']=='unknown':
   interrogative=text.startswith(('需核对','需确认','尚需')) or text.endswith(('?','？')) or re.search('是否|有无|何时|何种|多少|哪些|如何|为何|什么',text)
   if not interrogative or language_issues(text,question):raise ModelError('未知事实必须保留为待核实问题，不得先作违法断言。')
  cleaned.append(dict(status=f['status'],text=text))
 rows=[]
 for m in materials:
  if not isinstance(m,dict) or m.get('issue_id') not in issues or m.get('element') not in ELEMENTS:raise ModelError('材料台账争点或要件无效。')
  name=m.get('name');q=m.get('question');roles=m.get('claim_roles')
  if not isinstance(name,str) or not 2<=len(name)<=80 or not isinstance(q,str) or not 4<=len(q)<=300:raise ModelError('材料台账缺少材料名称或事实问题。')
  interrogative=q.startswith(('是否','有无','何时','何种','多少','哪些')) or q.endswith(('?','？')) or '是否' in q or '有无' in q
  if not interrogative or re.search('必然|已违法|当然无效',name) or re.search('^(?:是否)(?:已违法|有权解除|应当赔偿|当然无效)',q):raise ModelError('材料台账只能提出事实核对问题，不能发布法律结论：'+q[:120])
  if not isinstance(roles,list) or not 1<=len(roles)<=3 or any(r not in ALLOWED_ROLES for r in roles):raise ModelError('材料台账关联分析类型无效。')
  if m.get('status','not_submitted')!='not_submitted':raise ModelError('仅文字提问不能伪称已收到或查验原件。')
  rows.append(dict(id='M'+str(len(rows)+1),issue_id=m['issue_id'],element=m['element'],name=name,question=q,claim_roles=list(dict.fromkeys(roles)),status='not_submitted'))
 return dict(facts=cleaned,materials=rows)

def ledger_quality(ledger,plan,verification):
 accepted=[c for c in verification.get('checks',[]) if c['status']=='supported'];missing=[]
 if not ledger.get('facts'):missing.append('事实台账未建立')
 for issue in plan['issues']:
  rows=[m for m in ledger.get('materials',[]) if m['issue_id']==issue['id']]
  if not rows:missing.append(issue['id']+'没有材料核对项')
  if issue.get('requires_notice'):
   for element in set(NOTICE_MATERIALS)-{m['element'] for m in rows}:missing.append(issue['id']+'缺少'+ELEMENTS[element]+'材料任务')
 for m in ledger.get('materials',[]):
  if not any(c['issue_id']==m['issue_id'] and c.get('role') in m['claim_roles'] for c in accepted):missing.append(m['id']+'缺少关联的已核验分析')
 return dict(passed=not missing,facts=len(ledger.get('facts',[])),materials=len(ledger.get('materials',[])),gaps=missing)

def render_ledger(ledger,plan,verification,labels):
 accepted=[c for c in verification.get('checks',[]) if c['status']=='supported'];titles={i['id']:i.get('title',i['question']) for i in plan['issues']}
 context=ledger.get('case_context',{});documents=context.get('documents',[])
 lines=['### 事实材料台账',('本次已选入'+str(len(documents))+'份电子材料；以下候选关联按材料类别匹配，不表示已查验原件或已证明要件。' if documents else '“本次未提交原件”只描述本次文字输入，不表示材料不存在。台账是补证计划，未进行独立调查。')]
 for m in ledger.get('materials',[]):
  linked=[c for c in accepted if c['issue_id']==m['issue_id'] and c.get('role') in m['claim_roles']]
  refs='；'.join(c['claim_id']+'（'+labels[c['role']]+'）' for c in linked)
  kinds={'obligation':['contract'],'termination_period':['contract'],'penalty':['contract','payment'],'cure':['notice','communication'],'notice_arrival':['notice','communication'],'notice_condition':['notice'],'court_service':['other'],'loss':['payment'],'mitigation':['payment','communication']}.get(m['element'],[])
  matched=[d['name'] for d in documents if d['kind'] in kinds]
  status='已接收候选电子材料：'+'、'.join(matched)+'；未核实原件和证明力。' if matched else ('暂无明确匹配的电子材料，待收集核对。' if documents else '本次未提交原件，待收集核对。')
  lines+=['#### '+m['id']+' · '+m['name'],'- 材料状态：'+status,'- 待证明事实：'+m['question'],
   '- 对应要件：'+ELEMENTS[m['element']],'- 关联争点：'+titles[m['issue_id']],'- 影响分析：'+(refs or '相关分析尚未通过核验，暂不据此判断法律后果。')]
 return lines
