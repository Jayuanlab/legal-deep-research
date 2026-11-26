import unittest
from unittest.mock import patch
import research_engine as engine
from test_engine import D1,REF,PLAN,UNITS
class RepairTests(unittest.TestCase):
 def test_repairs_only_rejected_role_and_retains_accepted_verbatim(self):
  rows=[dict(c,claim_id=c['id'],status='unsupported' if c['role']=='action' else 'supported',reason='需修订') for c in UNITS]
  previous=dict(checks=rows,cited=['E563'],invalid=[],queries=[],accepted=4,passed=False,status='部分未通过',scope='fixture')
  action=dict(UNITS[-1],statement='建议先核对履行及催告条件。')
  calls=[]
  def ask(instruction,payload,tokens):
   calls.append(payload)
   if 'target_roles' in payload:
    self.assertEqual([r['role'] for r in payload['target_roles']],['action'])
    self.assertNotIn('checks',payload)
    return dict(report_version=2,facts=[],claims=[action,dict(action,role='conclusion',statement='未请求的额外结论不得进入正文。')])
   return dict(checks=[dict(claim_id='R1',verdict='supported',reason='来源支持',fact_verdict='conditional',fact_reason='需核对条件')],queries=[])
  budget=engine.Budget();budget.ask=ask
  result=engine.repair_verified('问题',PLAN,[D1],{},previous,budget)
  self.assertTrue(result['passed']);self.assertEqual(result['accepted'],5);self.assertEqual(len(calls),2)
  self.assertEqual(result['checks'][:4],rows[:4]);self.assertEqual(result['checks'][-1]['statement'],action['statement'])
  self.assertEqual(result['repair_excluded_roles'][0]['role'],'conclusion')
  self.assertNotIn('未请求的额外结论',str(result['checks']))

 def test_overbroad_cure_deadline_invalidation_is_not_published(self):
  c=dict(UNITS[0],statement='若合理期限过短，则催告无效，解除权不成立。')
  with patch.object(engine,'complete') as model:
   result=engine.validate_claims([c],[D1],engine.Budget())
  model.assert_not_called();self.assertEqual(result['accepted'],0)

 def test_rebuttal_of_invalid_deadline_assertion_is_not_program_rejected(self):
  from report_document import structural_errors
  c=dict(UNITS[0],statement='若供应商主张催告合理期限过短致使催告无效，现有依据不足以直接断言催告无效，须核实合理期限是否实际届满。')
  self.assertFalse(structural_errors(c,{'E563':D1}))

 def test_parenthesized_case_identifier_must_be_declared(self):
  c=dict(UNITS[0],statement='重庆房屋案(CT16210N8)可供比较。')
  with patch.object(engine,'complete') as model:result=engine.validate_claims([c],[D1],engine.Budget())
  model.assert_not_called();self.assertEqual(result['accepted'],0)

 def test_conditional_counterargument_checks_special_contract_deadline(self):
  from report_document import structural_errors
  c=dict(UNITS[0],statement='若供应商主张解除权已过一年期间，须核实合理期限是否实际届满及是否存在合同特别期限。')
  self.assertFalse(structural_errors(c,{'E563':dict(D1,article='564')}))

if __name__=='__main__':unittest.main()
