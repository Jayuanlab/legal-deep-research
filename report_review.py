"""Conservative claim gates and a separate, reject-only consistency pass."""
import re
from matter_evidence import reference_error

CONDITIONAL=re.compile(r'^(?:若|如果|倘若|假如|如经|如未|在.{0,30}(?:前提|情况|条件))')
ATTRIBUTED=re.compile('材料|合同|协议|凭证|记录|邮件|文书')

def factual_assertion_errors(statement,question,context=None):
 errors=[];context=context or {};disputed={d['slot'] for d in context.get('differences',[])}
 document_status=[o for o in context.get('observations',[]) if o['slot']=='substitute_transaction' and not o.get('disputed')]
 for sentence in re.split(r'[。；;\n]',statement):
  text=sentence.strip()
  if not text:continue
  # A later conditional sentence cannot cure an earlier assertion.
  about_case=bool(re.search('本案|买方|采购方|守约方|我方',text))
  assertion=re.search(r'(?:本案|买方|采购方|守约方|我方|均)[^。；]{0,45}(?:未(?:实施|进行|发生)|没有(?:实施|进行)|已(?:实施|进行)|已经(?:另行采购|进行))[^。；]{0,12}(?:替代交易|替代采购|另行采购)',text)
  conditional=bool(CONDITIONAL.match(text))
  if assertion and about_case and not conditional:
   attributed=bool(ATTRIBUTED.search(text) and re.search('记载|载明|显示|记述|据|根据',text))
   wanted='no' if re.search('未(?:实施|进行)|没有(?:实施|进行)|未另行采购|没有另行采购',text) else 'yes'
   user_values=set()
   for sentence in re.split(r'[。；;\n]',question or ''):
    if re.search('是否|有无|[?？]|若|如果|假如',sentence):continue
    if re.search(r'(?:我方|买方|采购方|守约方)(?:尚未|未|没有)(?:实施|进行|另行采购)[^。；]{0,12}(?:替代交易|替代采购)?',sentence):user_values.add('no')
    elif re.search(r'(?:我方|买方|采购方|守约方)(?:已经|已|确实)(?:实施|进行|另行采购)[^。；]{0,12}(?:替代交易|替代采购)?',sentence):user_values.add('yes')
   explicit_user=wanted in user_values
   if not (explicit_user or (document_status and attributed)):
    if not (attributed and 'substitute_transaction' in disputed and re.search('差异|冲突|待核|不同|不能确认',text)):errors.append('事实前提检查：本案替代交易情况未获确认，不能先写成已实施或未实施，再在后文补若条件。')
   if document_status and attributed:
    if wanted not in {o['value'] for o in document_status}:errors.append('材料记载与本案替代交易断言方向相反。')
  if disputed and re.search('已查明|确定无疑|事实已确认|经独立查验',text):errors.append('案卷存在未解决差异，不得把材料记载写成已经查明的事实。')
  if not conditional and re.search(r'(?:本案|我方|买方|采购方|守约方)[^。；]{0,20}(?:未另行采购|没有另行采购|已另行采购)',text) and not document_status and not (assertion and explicit_user):
   errors.append('事实前提检查：未提供本案另行采购情况的依据。')
 return list(dict.fromkeys(errors))

def legal_condition_errors(claim,sources):
 errors=[];text=claim['statement']
 for sentence in re.split(r'[。；;]',text):
  direct=bool(re.search(r'(?:直接|未[^，。；]{0,8}通知)[^。；]{0,12}(?:起诉|诉讼|仲裁)',sentence))
  if direct and '解除' in sentence and re.search('送达|副本',sentence) and '确认' not in sentence:
   errors.append('直接起诉或仲裁的解除时点判断遗漏法院或仲裁机构确认主张的条件；摘要也必须保留。')
 if all(x in text for x in ('主要债务','催告')) and re.search('宽限期|合理期限',text) and '解除' in text:
  refs=[sources.get(r.get('source_id'),{}) for r in claim.get('references',[]) if isinstance(r,dict)]
  if refs and not any(all(x in d.get('text','') for x in ('主要债务','催告')) and re.search('合理期限|宽限期',d.get('text','')) for d in refs):
   errors.append('解除权成立条件缺少直接依据；通知生效或违约金条款不能替代主要债务、催告和合理期限的依据。')
 return errors

def document_fact_errors(statement,refs,context):
 errors=[reference_error(r,context) for r in refs];errors=[e for e in errors if e]
 if not refs:errors.append('材料事实缺少可定位的原文引用')
 if not (ATTRIBUTED.search(statement) and re.search('记载|载明|显示|据|根据',statement)):errors.append('材料支持的事实必须明确归属于材料陈述，不能冒充独立查明。')
 used={r.get('span_id') for r in refs if isinstance(r,dict)}
 disputed={o['span_id'] for o in context.get('observations',[]) if o.get('disputed')}
 if used&disputed and not re.search('差异|冲突|不同|待核|尚需|不能确认|尚不能',statement):errors.append('所引材料涉及未解决差异，须明确保留差异或待核条件。')
 return errors

def consistency_review(question,ledger,context,verification,budget):
 """This pass can reject supported units, never promote rejected units."""
 checks=[dict(c) for c in verification['checks']];flags=[];rejected=[]
 accepted=[c for c in checks if c['status']=='supported']
 if not accepted:return dict(verification,consistency_review=dict(status='no_publishable_units',flags=[]))
 data=budget.ask('只找报告中的事实越界、台账矛盾和关键条件遗漏，不重新判断法律支持，不把任何被拒内容提升为通过。'
  '输出{"flags":[{"claim_id":"真实编号","quote":"该单元中4字以上逐字问题片段","kind":"unknown_fact|ledger_conflict|condition_missing|material_conflict","reason":"具体问题"}]}。'
  '同一段先认定本案未实施替代交易，再写若条件，仍应拦截；材料记载不等于查明事实，有差异不能自动选一份当真。'
  '摘要和规范段不得遗漏直接诉/仲裁路径须确认主张的条件。无具体问题返回空数组，不为凑数量挑格式。',
  dict(question=question,ledger=ledger,case_context=context,claims=[dict(id=c['claim_id'],statement=c['statement'],role=c.get('role')) for c in accepted]),1600)
 raw=data.get('flags',[])
 if not isinstance(raw,list):raise ValueError('一致性检查结构无效。')
 for f in raw[:20]:
  if not isinstance(f,dict) or f.get('kind') not in ('unknown_fact','ledger_conflict','condition_missing','material_conflict'):continue
  c=next((c for c in checks if c['claim_id']==f.get('claim_id') and c['status']=='supported'),None)
  quote=f.get('quote');reason=f.get('reason')
  if c and isinstance(quote,str) and len(quote)>=4 and quote in c['statement'] and isinstance(reason,str) and reason.strip():
   if re.search('待查明|待核|待确认|尚不明确|尚不能确认',quote) and re.search('应(?:当)?(?:直接)?认定.{0,20}(?:未|没有|不存在)',reason):
    rejected.append(dict(flag=f,reason='复核理由把缺少证据推成不存在事实，不能据此否决保留未知的陈述。'));continue
   if f['kind']=='condition_missing' and '确认' in quote and re.search('副本送达|送达时',quote) and re.search('是否.{0,10}送达',reason):
    rejected.append(dict(flag=f,reason='被引条件句已保留确认及副本送达条件；不能仅因个案送达待核而否定条件式规则。'));continue
   c.update(status='uncertain',reason='全文一致性检查：'+reason[:600]);flags.append(f)
 result=dict(verification,checks=checks);result['accepted']=sum(c['status']=='supported' for c in checks);result['passed']=bool(checks) and all(c['status']=='supported' for c in checks)
 result['cited']=sorted({r['source_id'] for c in checks if c['status']=='supported' for r in c['references']})
 result['status']='主张引用检查通过' if result['passed'] else '部分分析未通过核验'
 result['consistency_review']=dict(status='completed',flags=flags,rejected_flags=rejected)
 return result
