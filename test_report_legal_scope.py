import unittest
from unittest.mock import patch
from report_document import structural_errors
import research_engine as engine

class LegalScopeTests(unittest.TestCase):
 def test_inspection_deadline_cannot_support_cure_deadline(self):
  doc=dict(id='L12',doc_type='law',text='具体认定民法典第六百二十一条第二款规定的合理期限时，应当综合交易性质。')
  claim=dict(id='K1',issue_id='I1',role='application',statement='催告履行的合理期限应综合交易性质判断。',references=[dict(source_id='L12',quote='应当综合交易性质')])
  with patch.object(engine,'complete') as model:
   result=engine.validate_claims([claim],[doc],engine.Budget(),question='催告后仍未履行')
  model.assert_not_called();self.assertEqual(result['accepted'],0)
  self.assertIn('检验瑕疵',result['checks'][0]['reason'])
  claim['statement']='应区分检验瑕疵通知与催告履行的合理期限，不能直接移用。'
  self.assertFalse(structural_errors(claim,{'L12':doc}))

 def test_one_year_deadline_retains_default_rule_conditions(self):
  doc=dict(id='L564',doc_type='law',article='564',text='法律没有规定或者当事人没有约定解除权行使期限，一年内不行使，该权利消灭。')
  claim=dict(role='action',statement='建议核实自身是否在一年解除权期限内行使。',references=[dict(source_id='L564',quote='一年内不行使，该权利消灭')])
  self.assertTrue(structural_errors(claim,{'L564':doc}))
  claim['statement']='建议先核对合同约定及法律特别规定，再核实补充适用的一年解除权期限。'
  self.assertFalse(structural_errors(claim,{'L564':doc}))

if __name__=='__main__':unittest.main()
