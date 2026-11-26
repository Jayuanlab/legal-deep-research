"""Typed, verified legal report units. No unverified narrative publication path."""
import re
from models import ModelError
from notice_rules import notice_errors
from report_ledger import render_ledger

VERSION='legal-workbench-v4'
ROLES={'conclusion':'倾向结论','rule':'规范要点','application':'事实与要件适用','supporting':'支持理由','counterargument':'可能抗辩与回应','case_comparison':'类案比较','action':'行动建议','notice':'解除通知的行使与生效','strategy':'方案比较','recommendation':'有条件的研究建议'}
REQUIRED={'conclusion','application','supporting','counterargument','action'}

def normalized(s):return re.sub(r'\s+','',s)

def parse_document(data,question,plan):
 if data.get('report_version') not in (2,3):raise ModelError('报告缺少受支持的结构标识。')
 raw=data.get('claims')
 if not isinstance(raw,list) or not 1<=len(raw)<=28:raise ModelError('报告分析单元数量必须为1至28项。')
 issues={i['id'] for i in plan['issues']};claims=[]
 for i,item in enumerate(raw,1):
  if not isinstance(item,dict) or item.get('issue_id') not in issues or item.get('role') not in ROLES:raise ModelError('报告单元争点或类型无效。')
  statement=item.get('statement');refs=item.get('references')
  if not isinstance(statement,str) or not statement.strip() or len(statement)>2200 or not isinstance(refs,list) or not 1<=len(refs)<=4:raise ModelError('报告单元缺少完整文字或引用。')
  claims.append(dict(id='K'+str(i),issue_id=item['issue_id'],role=item['role'],statement=statement.strip(),references=refs,case_source_id=item.get('case_source_id'),priority=item.get('priority',2),option_key=item.get('option_key')))
 facts=data.get('facts',[])
 if not isinstance(facts,list) or len(facts)>12:raise ModelError('报告事实结构无效。')
 cleaned=[]
 for f in facts:
  if not isinstance(f,dict) or f.get('status') not in ('provided','unknown'):raise ModelError('事实只能标为题设陈述或待确认，不得伪称已调查。')
  text=f.get('text')
  if not isinstance(text,str) or not 4<=len(text)<=500:raise ModelError('事实文字长度无效。')
  if f['status']=='provided' and normalized(text) not in normalized(question):raise ModelError('题设事实无法逐字匹配原问题。')
  if f['status']=='unknown' and not (text.startswith(('是否','有无','需核对','需确认','尚需')) or text.endswith(('?','？'))):raise ModelError('未知事实必须写成待核对事项，不得直接断言。')
  cleaned.append(dict(status=f['status'],text=text))
 return dict(report_version=data['report_version'],claims=claims,facts=cleaned,limitations=[])

def structural_errors(claim,sources):
 errors=notice_errors(claim,sources);role=claim.get('role','conclusion')
 if (re.search('合理期限(?:设置)?过短.{0,20}(?:催告无效|解除权不成立)',claim['statement'])
     and not (re.search('不足以直接断言|不能直接断言|不当然|不能仅以|而非仅以',claim['statement']) and '实际届满' in claim['statement'])):
  errors.append('仅以催告期限过短，现有依据不足以直接断言催告无效或解除权不成立；须核实合理期限是否实际届满。')
 if role=='case_comparison':
  key=claim.get('case_source_id');d=sources.get(key,{})
  if d.get('doc_type')!='case' or key not in {r.get('source_id') for r in claim['references'] if isinstance(r,dict)}:errors.append('类案比较必须引用本次证据中的真实案例，且明确案例编号。')
  for pattern in ('相似|共同','差异|不同|区别','参考|用途|适用|借鉴'):
   if not re.search(pattern,claim['statement']):errors.append('类案比较缺少相似点、关键差异或适用边界。');break
 for ref in claim['references']:
  if isinstance(ref,dict) and sources.get(ref.get('source_id'),{}).get('reference_status')=='not_reference':errors.append('引用了已排除的失效或历史版本。')
  source=sources.get(ref.get('source_id'),{}) if isinstance(ref,dict) else {}
  if (source.get('doc_type')=='law' and '第六百二十一条第二款' in source.get('text','')
      and re.search('催告|迟延履行',claim['statement']) and '合理期限' in claim['statement']
      and not re.search('不能|不得|不适用|不可援引|应区分',claim['statement'])):
   errors.append('检验瑕疵通知的合理期限规则不能直接用于催告履行的合理期限。')
  if (source.get('doc_type')=='law' and source.get('article')=='564' and '一年' in claim['statement']
      and not re.search('法律没有规定|法律无规定|没有约定|无约定|未约定|无特别规定|无特别约定|合同约定|约定期限|核实.{0,30}合同特别期限',claim['statement'])):
   errors.append('一年解除权期限的适用前提未交代，须先核对法律及合同约定期限。')
 if re.search(r'本所(?:律师)?(?:已|经)|经本(?:系统|平台)实地|已(?:联系|访谈|调取原件)|保证胜诉|胜诉率\s*\d',claim['statement']):errors.append('不得虚构律师调查、已经执行的外部动作或胜诉保证。')
 return errors

def quality(plan,verification,evidence):
 accepted=[r for r in verification.get('checks',[]) if r['status']=='supported'];missing=[]
 for issue in plan.get('issues',[]):
  roles={r.get('role','conclusion') for r in accepted if r['issue_id']==issue['id']}
  required=REQUIRED|({'notice'} if issue.get('requires_notice') else set())
  for role in sorted(required-roles):missing.append(dict(issue_id=issue['id'],section=role,reason=ROLES[role]+'尚无通过核验的内容'))
 case_present=any(d['doc_type']=='case' for d in evidence)
 comparisons=[r for r in accepted if r.get('role')=='case_comparison']
 cases={next((d.get('parent_id') or d['id'] for d in evidence if d['id']==c.get('case_source_id')),c.get('case_source_id')) for c in comparisons}
 return dict(passed=bool(plan.get('issues')) and not missing,missing_sections=missing,case_comparisons=len(comparisons),distinct_cases=len(cases),case_material_available=case_present,
  case_status=f'共{len(cases)}件案例、{len(comparisons)}项通过核验的有限比较' if comparisons else ('已召回案例，但尚无比较通过核验，不作为本案结论的案例论据' if case_present else '本次未检得可供比较的案例，不能据此断言不存在类案'))

def render_document(plan,assessment,verification,document,evidence,question,stop_reason):
 accepted=[r for r in verification.get('checks',[]) if r['status']=='supported'];sources={d['id']:d for d in evidence};q=quality(plan,verification,evidence)
 def paragraph(row):return row['statement']+' '+''.join('['+key+']' for key in dict.fromkeys([r['source_id'] for r in row['references']]+[r['span_id'] for r in row.get('fact_references',[])]))
 lines=['# 专项法律研究报告','## 一、结论摘要']
 if not accepted:lines.append('证据不足，当前不能形成通过核验的法律结论。')
 for issue in plan.get('issues',[]):
  cs=[r for r in accepted if r['issue_id']==issue['id'] and r.get('role','conclusion')=='conclusion']
  lines+=['### '+issue.get('title',issue['question'])]+([paragraph(r) for r in cs] or ['该争点暂无通过核验的结论，保留待研究。'])
 lines+=['## 二、事实与材料基础','研究问题（用户原文）：'+question,'本报告以用户题设为分析前提，未独立查验合同、凭证或进行律师调查。']
 for f in (document or {}).get('facts',[]):lines.append(('- 题设陈述：' if f['status']=='provided' else '- 待核实：')+f['text'])
 if not (document or {}).get('facts'):lines.append('当前没有可独立列示的事实记录，具体前提及缺口见下列争点与待补材料。')
 if (document or {}).get('materials'):lines+=render_ledger(document,plan,verification,ROLES)
 lines+=['## 三、逐争点分析']
 for issue in plan.get('issues',[]):
  lines+=['### '+issue.get('title',issue['question'])]
  for role in ('rule','application','supporting','counterargument','notice'):
   rows=[r for r in accepted if r['issue_id']==issue['id'] and r.get('role')==role]
   if rows:lines+=['#### '+ROLES[role]]+[paragraph(r) for r in rows]
   elif role not in ('rule','notice') or (role=='notice' and issue.get('requires_notice')):lines+=['#### '+ROLES[role],'该部分缺少通过核验的分析，不据此作进一步判断。']
 lines+=['## 四、类案比较',q['case_status']]
 grouped={}
 for r in accepted:
  if r.get('role')!='case_comparison':continue
  d=sources.get(r.get('case_source_id'),{});grouped.setdefault(d.get('parent_id') or d.get('id'),[]).append(r)
 for rows in grouped.values():
  d=sources[rows[0]['case_source_id']];identity='；'.join(str(d.get(k)) for k in ('guiding_number','case_number','court','date','kind') if d.get(k))
  lines+=['### '+d.get('title','案例'),identity or '案例身份信息以官方发布文本为准。']
  for r in rows:lines+=['对应争点：'+next((i.get('title',i['question']) for i in plan['issues'] if i['id']==r['issue_id']),r['issue_id']),paragraph(r)]
 lines+=['## 五、行动建议']
 for issue in plan.get('issues',[]):
  rows=[r for r in accepted if r['issue_id']==issue['id'] and r.get('role')=='action']
  lines+=['### '+issue.get('title',issue['question'])]+([paragraph(r) for r in rows] or ['暂缺经过核验的行动建议，需先补足该争点的事实或法律依据。'])
 lines+=['## 六、待补材料与适用边界']
 for f in dict.fromkeys(plan.get('missing_facts',[])+assessment.get('missing_facts',[])):lines.append('- 待核实事项：'+f)
 for row in assessment.get('coverage',[]):
  if not row['sufficient']:lines.append('- 法律证据缺口 '+row['issue_id']+'：'+row['reason'])
 for m in q['missing_sections']:lines.append('- 分析缺口 '+m['issue_id']+'：'+m['reason'])
 rejected=[r for r in verification.get('checks',[]) if r['status']!='supported']
 if rejected:lines.append('未通过核验的分析单元不进入正文；逐项拒绝理由保留在主张核验记录中。')
 lines+=['法律资料仅来自本地库；题设事实、规范效力与时间适用仍须核实。未检得反例不等于不存在相反裁判。',
  '引文匹配与模型支持性检查不能证明全部法律结论正确，也不能替代人工判断。',stop_reason,'## 七、规范与案例依据']
 cited=sorted({r['source_id'] for row in accepted for r in row['references']})
 for key in cited:
  d=sources[key];meta='；'.join(str(d.get(k)) for k in ('version','kind') if d.get(k));v=d.get('validity',{}).get('label')
  if v:meta+='；'+v
  lines+=['['+key+'] '+d['title']+'。'+meta]
  if d.get('url'):lines.append('[官方来源]('+d['url']+')')
 if not cited:lines.append('暂无通过核验的引据。')
 return '\n\n'.join(lines)
