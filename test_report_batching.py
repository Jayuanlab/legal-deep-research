import unittest
from unittest.mock import patch
import research_engine as engine
from test_engine import D1,REF,ROLES
from models import ModelServiceError
import time

class BatchingTests(unittest.TestCase):
 def test_expired_repair_keeps_previous_verified_units(self):
  from test_engine import PLAN,DRAFT
  budget=engine.Budget()
  def expired(*args,**kwargs):
   budget.started=time.monotonic()-budget.seconds-1
   raise ModelServiceError('timeout','text',1,True)
  prior=dict(checks=[dict(claim_id='K1',issue_id='I1',role='conclusion',statement='若符合条件，可主张解除。',references=[REF],status='supported')],cited=['E563'],invalid=[],queries=[],accepted=1,passed=False,status='仍有结构缺口')
  with patch.object(engine,'make_plan',return_value=PLAN),patch.object(engine,'assess',return_value=dict(sufficient=True,coverage=[],missing_facts=[])),patch.object(engine,'retrieve',return_value=[D1]),patch.object(engine,'draft',return_value=DRAFT),patch.object(engine,'repair_verified',side_effect=expired),patch.object(engine,'validate_claims',return_value=prior),patch.object(engine,'public_config',return_value={'text_model':'fixture'}):
   result=engine.research('是否可以解除合同',budget=budget)
  self.assertEqual(result['outcome'],'limited');self.assertEqual(result['verification']['accepted'],1)
  self.assertIn('此前核验通过',result['stop_reason']);self.assertIn(prior['checks'][0]['statement'],result['report'])

 def test_issue_batches_merge_unique_ids_without_losing_roles(self):
  plan=dict(issues=[dict(id='I1',question='解除'),dict(id='I2',question='赔偿')])
  calls=[]
  def ask(instruction,payload,tokens):
   issue=payload['plan']['issues'];self.assertEqual(len(issue),1);calls.append((issue[0]['id'],tokens))
   return dict(report_version=2,facts=[],claims=[dict(id='K1',issue_id=issue[0]['id'],role=role,statement='需要核对履行条件。',references=[REF]) for role in ROLES])
  budget=engine.Budget();budget.ask=ask
  result=engine.draft('问题',plan,[D1],{},budget)
  self.assertEqual(len(result['claims']),10);self.assertEqual(len({c['id'] for c in result['claims']}),10)
  self.assertEqual({c['issue_id'] for c in result['claims']},{'I1','I2'})
  self.assertTrue(all(t<=3000 for _,t in calls))

 def test_small_verification_batches_preserve_all_rejections(self):
  claims=[dict(id='K'+str(i),issue_id='I1',role='application',statement='若满足条件，可以解除。',references=[REF]) for i in range(15)]
  def ask(instruction,payload,tokens):
   self.assertLessEqual(len(payload['claims']),6);self.assertLessEqual(tokens,2600)
   return dict(checks=[dict(claim_id=c['id'],verdict='unsupported' if c['id']=='K8' else 'supported',reason='依据核对',fact_verdict='conditional',fact_reason='以未知条件为前提') for c in payload['claims']],queries=[])
  budget=engine.Budget();budget.ask=ask
  result=engine.validate_claims(claims,[D1],budget,question='问题')
  self.assertEqual(len(result['checks']),15);self.assertEqual(result['accepted'],14);self.assertFalse(result['passed'])
  self.assertEqual(next(c for c in result['checks'] if c['claim_id']=='K8')['status'],'unsupported')

if __name__=='__main__':unittest.main()
