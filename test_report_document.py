import copy,unittest,json
from unittest.mock import patch
import research_engine as engine
from report_document import parse_document,structural_errors,quality,render_document
from models import ModelError
from test_engine import D1,PLAN,CLAIM,REF,DRAFT,SUPPORTED

class ReportDocumentTests(unittest.TestCase):
 def test_fact_quotes_are_verbatim_and_cannot_claim_investigation(self):
  doc=copy.deepcopy(DRAFT);doc['facts']=[dict(status='provided',text='供应商已经停业')]
  with self.assertRaises(ModelError):parse_document(doc,'供应商逾期交付设备',PLAN)
  doc['facts']=[dict(status='verified',text='供应商逾期交付设备')]
  with self.assertRaises(ModelError):parse_document(doc,'供应商逾期交付设备',PLAN)
  doc['facts']=[dict(status='provided',text='供应商逾期交付设备'),dict(status='unknown',text='是否已发出解除通知？')]
  self.assertEqual(len(parse_document(doc,'供应商逾期交付设备',PLAN)['facts']),2)
 def test_vague_or_legacy_generation_is_not_accepted_as_v2(self):
  for data in [dict(claims=[CLAIM]),dict(DRAFT,claims=[dict(CLAIM,role='invented')])]:
   with self.assertRaises(ModelError):parse_document(data,'合同解除',PLAN)
 def test_case_comparison_must_reference_actual_case_and_boundaries(self):
  c=dict(CLAIM,role='case_comparison',case_source_id='E563',statement='相似之处为争点，差异为事实未知，仅可参考规则。')
  self.assertTrue(structural_errors(c,{'E563':D1}))
  case=dict(D1,id='CT1',doc_type='case');c['case_source_id']='CT1';c['references']=[dict(REF,source_id='CT1')]
  self.assertEqual(structural_errors(c,{'CT1':case}),[])
  c['statement']='两案完全相同，所以必然胜诉。'
  self.assertTrue(structural_errors(c,{'CT1':case}))
 def test_law_status_and_generic_source_ids_cannot_bypass_validation(self):
  c=dict(CLAIM,role='action',statement='建议核对条文 [J999A2]')
  with patch.object(engine,'complete') as complete:r=engine.validate_claims([c],[D1],engine.Budget())
  self.assertEqual(r['accepted'],0);complete.assert_not_called()
  with patch.object(engine,'complete') as complete:r=engine.validate_claims([CLAIM],[dict(D1,reference_status='not_reference')],engine.Budget())
  self.assertEqual(r['accepted'],0);complete.assert_not_called()
 def test_rejected_application_and_actions_have_no_rendering_backdoor(self):
  checks=[dict(claim_id='K1',issue_id='I1',role='conclusion',status='supported',statement='若满足条件可分析解除。',references=[REF]),
          dict(claim_id='K2',issue_id='I1',role='action',status='unsupported',statement='必须向甲公司支付一百万元。',references=[REF]),
          dict(claim_id='K3',issue_id='I1',role='application',status='uncertain',statement='已经实地查验供应商无财产。',references=[REF])]
  text=render_document(PLAN,{},dict(checks=checks),dict(facts=[]),[D1],'合同解除','证据有限')
  self.assertNotIn('一百万元',text);self.assertNotIn('无财产',text)
  self.assertFalse(quality(PLAN,dict(checks=checks),[D1])['passed'])
 def test_all_roles_receive_independent_semantic_and_fact_checks(self):
  doc=parse_document(DRAFT,'合同解除',PLAN)
  with patch.object(engine,'complete',return_value=(json.dumps(SUPPORTED,ensure_ascii=False),'fixture')) as complete:
   r=engine.validate_claims(doc['claims'],[D1],engine.Budget(),question='合同解除')
  sent=json.loads(complete.call_args.args[1]);self.assertEqual({c['role'] for c in sent['claims']},{'conclusion','application','supporting','counterargument','action'})
  self.assertTrue(quality(PLAN,r,[D1])['passed'])
  self.assertIn('未检得',quality(PLAN,r,[D1])['case_status'])
 def test_invented_lawyer_investigation_is_blocked_before_semantic_model(self):
  c=dict(CLAIM,role='application',statement='本所律师已向供应商实地调查，确认其违法。')
  self.assertTrue(structural_errors(c,{'E563':D1}))

if __name__=='__main__':unittest.main()
