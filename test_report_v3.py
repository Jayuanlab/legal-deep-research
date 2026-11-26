import copy,json,unittest
from unittest.mock import patch
from report_ledger import parse_ledger,ledger_quality,complete_requests,NOTICE_MATERIALS
from notice_rules import requires_notice,notice_errors,NOTICE_QUERY
from report_document import quality
from models import ModelError
import research_engine as engine
from test_engine import PLAN,D1,GOOD,DRAFT,SUPPORTED,REF

NOTICE=dict(id='E565',title='民法典 第565条',doc_type='law',law_name='中华人民共和国民法典',article='565',text='当事人一方依法主张解除合同的，应当通知对方。合同自通知到达对方时解除；通知载明一定期限内不履行则自动解除，合同自期限届满时解除。直接起诉或仲裁，经确认主张的，自起诉状副本或者仲裁申请书副本送达对方时解除。')
STATEMENT='依法享有解除权时，普通解除通知到达对方时生效；如通知附期限且债务人届满未履行，合同于期限届满解除。未先通知而直接起诉或申请仲裁，经法院或仲裁机构确认主张的，自起诉状或仲裁申请书副本送达对方时解除。'
NCLAIM=dict(id='K6',issue_id='I1',role='notice',statement=STATEMENT,references=[dict(source_id='E565',quote='合同自通知到达对方时解除')])

def ledger(plan=PLAN):
 return dict(facts=[dict(status='provided',text='供应商逾期交付设备'),dict(status='unknown',text='是否发出解除通知？')],materials=[dict(issue_id=plan['issues'][0]['id'],name='通知及送达凭证',element=e,question='是否存在通知及送达记录？',claim_roles=['notice'],status='not_submitted') for e in ('cure','notice_arrival','court_service')])

class ReportV3Tests(unittest.TestCase):
 def test_termination_procedure_is_not_confused_with_post_termination_damages(self):
  self.assertTrue(requires_notice(dict(question='是否可以解除合同？')))
  self.assertFalse(requires_notice(dict(question='解除合同后能否要求赔偿损失？')))
 def test_generic_termination_law_cannot_replace_notice_law(self):
  c=dict(NCLAIM,references=[REF])
  self.assertTrue(notice_errors(c,{'E563':D1}))
  self.assertFalse(notice_errors(NCLAIM,{'E565':NOTICE}))
 def test_lodging_suit_is_not_a_substitute_for_service_and_confirmation(self):
  c=dict(NCLAIM,statement='依法解除时，通知到达即解除。附期限且届满未履行时解除。直接起诉或仲裁即解除。')
  errors=notice_errors(c,{'E565':NOTICE})
  self.assertTrue(any('副本' in e for e in errors));self.assertTrue(any('确认' in e for e in errors))
 def test_model_coverage_cannot_ignore_missing_article565(self):
  p=copy.deepcopy(PLAN);p['issues'][0]['requires_notice']=True
  b=engine.Budget();b.ask=lambda *a:GOOD
  result=engine.assess('是否解除合同',p,[D1],b)
  self.assertFalse(result['sufficient']);self.assertEqual(result['queries'][0],NOTICE_QUERY)
 def test_fact_ledger_is_verbatim_and_not_verified_documents(self):
  data=ledger();self.assertEqual(len(parse_ledger(data,'供应商逾期交付设备',PLAN)['materials']),3)
  for mutate in ('facts','status','conclusion'):
   d=copy.deepcopy(data)
   if mutate=='facts':d['facts'][0]['text']='供应商已停业'
   elif mutate=='status':d['materials'][0]['status']='verified'
   else:d['materials'][0]['question']='是否已违法并有权解除？'
   with self.assertRaises(ModelError):parse_ledger(d,'供应商逾期交付设备',PLAN)
 def test_material_purpose_cannot_link_to_rejected_analysis(self):
  p=parse_ledger(ledger(),'供应商逾期交付设备',PLAN)
  self.assertFalse(ledger_quality(p,PLAN,dict(checks=[]))['passed'])
  row=dict(NCLAIM,claim_id='K6',status='supported')
  self.assertTrue(ledger_quality(p,PLAN,dict(checks=[row]))['passed'])
 def test_question_about_contract_contents_need_not_start_with_whether(self):
  data=ledger();data['materials'][0]['question']='合同是否约定了解除情形和通知地址？'
  self.assertEqual(len(parse_ledger(data,'供应商逾期交付设备',PLAN)['materials']),3)
 def test_ledger_schema_repair_is_bounded_and_does_not_invent_verified_status(self):
  bad=ledger();bad['materials'][0]['question']='是否有权解除合同？'
  budget=engine.Budget();calls=[]
  def ask(*args):calls.append(args);return bad if len(calls)==1 else ledger()
  budget.ask=ask
  self.assertEqual(len(engine.make_ledger('供应商逾期交付设备',PLAN,budget)['materials']),3)
  self.assertEqual(len(calls),2)
 def test_full_flow_supplements_notice_and_persists_fact_material_checkpoint(self):
  p=copy.deepcopy(PLAN);p.update(report_schema=3);p['issues'][0]['requires_notice']=True
  facts=parse_ledger(ledger(p),'供应商逾期交付设备',p)
  d=copy.deepcopy(DRAFT);d['claims'].append(NCLAIM)
  supported=copy.deepcopy(SUPPORTED);supported['checks'].append(dict(claim_id='K6',verdict='supported',reason='第565条支持',fact_verdict='conditional',fact_reason='保留解除权及到达前提'))
  outputs=[GOOD,GOOD,supported];events=[]
  with patch.object(engine,'make_plan',return_value=p),patch.object(engine,'make_ledger',return_value=facts),patch.object(engine,'complete',side_effect=[(json.dumps(x,ensure_ascii=False),'fixture') for x in outputs]),patch.object(engine,'draft',return_value=d),patch.object(engine,'retrieve',side_effect=[[D1],[NOTICE]]) as fetch,patch.object(engine,'local_notice_sources',return_value=[NOTICE]),patch.object(engine,'public_config',return_value={'text_model':'fixture'}):
   result=engine.research('供应商逾期交付设备',emit=events.append)
  self.assertEqual(fetch.call_args_list[1].args[0],NOTICE_QUERY)
  self.assertEqual(result['outcome'],'complete');self.assertEqual(len(result['materials']),6)
  self.assertTrue(result['report_quality']['ledger']['passed'])
  self.assertIn('解除通知的行使与生效',result['report']);self.assertIn('事实材料台账',result['report'])
  self.assertTrue(any(e.get('checkpoint',{}).get('document',{}).get('materials') for e in events))
 def test_model_omitted_contract_and_wrong_notice_link_are_completed_without_new_facts(self):
  p=copy.deepcopy(PLAN);p['issues'][0]['requires_notice']=True
  raw=ledger();raw['materials'][1]['claim_roles']=['application']
  result=complete_requests(raw,p)
  self.assertEqual(result['facts'],raw['facts']);self.assertEqual(len(result['materials']),6)
  self.assertEqual({m['element'] for m in result['materials']},set(NOTICE_MATERIALS))
  self.assertEqual(next(m for m in result['materials'] if m['element']=='notice_arrival')['claim_roles'],['notice'])
  self.assertTrue(all(m['status']=='not_submitted' for m in result['materials']))
 def test_late_supplement_coverage_and_notice_survive_draft_context_limit(self):
  p=copy.deepcopy(PLAN);p['issues'][0]['requires_notice']=True
  junk=[dict(D1,id='J'+str(i),text='甲'*1700,retrieval_issues=['I1']) for i in range(9)]
  actual=dict(D1,retrieval_issues=[]);notice=dict(NOTICE,retrieval_issues=[])
  b=engine.Budget();seen=[]
  def ask(instruction,payload,tokens):seen.append(payload);return DRAFT
  b.ask=ask
  engine.draft('问题',p,junk+[actual,notice],dict(coverage=[dict(issue_id='I1',references=[REF])]),b)
  ids={d['id'] for d in seen[0]['evidence']}
  self.assertIn('E563',ids);self.assertIn('E565',ids)
 def test_separate_ledger_is_only_fact_authority_not_legacy_draft_facts(self):
  p=copy.deepcopy(PLAN);p['report_schema']=3
  data=copy.deepcopy(DRAFT);data['facts']=[dict(status='unknown',text='供应商已经确认违法')]
  b=engine.Budget();b.ask=lambda *a:data
  result=engine.draft('问题',p,[D1],{},b)
  self.assertEqual(result['facts'],[])
  self.assertEqual(len(result['claims']),5)
 def test_observed_embedded_whether_question_without_question_mark_is_unknown(self):
  data=ledger();data['facts']=[dict(status='unknown',text='催告通知是否到达供应商及合理期限是否届满')]
  self.assertEqual(len(parse_ledger(data,'供应商逾期交付设备',PLAN)['facts']),1)
  data['facts']=[dict(status='unknown',text='乙公司未经同意转委托个人信息，违反法律，是否需要通知')]
  with self.assertRaises(ModelError):parse_ledger(data,'供应商逾期交付设备',PLAN)
 def test_notice_deadline_wording_alone_does_not_establish_nonperformance(self):
  c=dict(NCLAIM,statement='依法享有解除权时，普通通知到达即解除。若通知载明债务人在一定期限内不履行则自动解除，则合同自期限届满时解除。未通知直接起诉或仲裁，经确认主张，自起诉状或仲裁申请书副本送达时解除。')
  self.assertTrue(any('实际未履行' in e for e in notice_errors(c,{'E565':NOTICE})))

if __name__=='__main__':unittest.main()
