"""Replay the observed privacy false positive, including a permissive model verdict."""
import json
import unittest
from unittest.mock import patch
from corpus import DATA
from research_engine import Budget,validate_claims,render
from fact_grounding import language_issues
import research_engine as engine

PREVIOUS=DATA.parent/'runs/a90c2c658fb14c779286758dbb3fd0ef.json'

class FactGroundingTests(unittest.TestCase):
    def setUp(self):
        self.job=json.loads(PREVIOUS.read_text(encoding='utf-8'));self.result=self.job['result']
        self.raw=next(c for c in self.result['verification']['checks'] if c['issue_id']=='I4')
        self.claim=dict(id='K4',issue_id='I4',statement=self.raw['statement'],references=self.raw['references'])

    def test_recorded_unknown_consent_claim_cannot_be_published(self):
        job=json.loads(PREVIOUS.read_text(encoding='utf-8'));r=job['result']
        failed=next(c for c in r['verification']['checks'] if c['issue_id']=='I4')
        claim=dict(id='K4',issue_id='I4',statement=failed['statement'],references=failed['references'])
        verdict=dict(checks=[dict(claim_id='K4',verdict='supported',reason='法条支持，末尾已经提示事实未知',fact_verdict='conditional',fact_reason='末尾有条件')],queries=[])
        with patch('research_engine.complete',return_value=(json.dumps(verdict,ensure_ascii=False),'fixture')):
            check=validate_claims([claim],r['evidence'],Budget(),question=job['question'],assessment=r['assessment'])
        self.assertEqual(check['accepted'],0)
        self.assertNotIn(claim['statement'],render(r['research_plan'],r['assessment'],check,[],''))

    def test_tail_caveat_and_unrelated_if_do_not_authorize_violation(self):
        for text in ['乙公司未经同意转委托，违反个人信息保护法，但是否同意尚未确认。',
                     '乙公司转委托个人信息处理违反法律。',
                     '经查明乙公司未经甲公司同意转委托个人信息，违反转委托限制。',
                     '若甲公司解除合同，乙公司未经同意转委托个人信息违反法律。']:
            with self.subTest(text=text):self.assertTrue(language_issues(text,self.job['question']))

    def test_genuine_condition_and_general_rule_are_allowed(self):
        for text in ['若经查明乙公司未经甲公司同意转委托个人信息，则可能违反转委托限制；目前尚未确认是否同意。',
                     '乙公司若未经甲公司同意转委托个人信息，则违反转委托限制。',
                     '受托人未经个人信息处理者同意不得转委托。']:
            with self.subTest(text=text):self.assertEqual(language_issues(text,self.job['question']),[])

    def test_explicit_case_fact_is_distinct_from_hypothetical(self):
        text='乙公司未经甲公司同意转委托个人信息，违反转委托限制。'
        self.assertEqual(language_issues(text,'乙公司未经甲公司同意转委托个人信息。'),[])
        self.assertTrue(language_issues(text,'如果乙公司未经甲公司同意转委托个人信息，应如何处理？'))
        self.assertTrue(language_issues(text,'尚未查明乙公司未经甲公司同意转委托个人信息是否属实。'))
        self.assertTrue(language_issues(text,'如经查明乙公司未经甲公司同意转委托个人信息，应如何处理？'))

    def test_missing_fact_verdict_fails_closed(self):
        claim={**self.claim,'statement':'若乙公司未经甲公司同意转委托个人信息，则可能违反转委托限制。'}
        verdict=dict(checks=[dict(claim_id='K4',verdict='supported',reason='法律支持')],queries=[])
        with patch('research_engine.complete',return_value=(json.dumps(verdict,ensure_ascii=False),'fixture')):
            check=validate_claims([claim],self.result['evidence'],Budget(),question=self.job['question'])
        self.assertEqual(check['accepted'],0)
        self.assertEqual(check['checks'][0]['fact_status'],'unestablished')

    def test_unknown_facts_override_supported_law(self):
        claim={**self.claim,'statement':'若乙公司未经甲公司同意转委托个人信息，则可能违反转委托限制。'}
        verdict=dict(checks=[dict(claim_id='K4',verdict='supported',reason='法律支持',fact_verdict='unestablished',fact_reason='把未披露当作未同意')],queries=[])
        with patch('research_engine.complete',return_value=(json.dumps(verdict,ensure_ascii=False),'fixture')):
            check=validate_claims([claim],self.result['evidence'],Budget(),question=self.job['question'])
        self.assertEqual(check['accepted'],0)

    def test_grounded_facts_require_original_question_quotes(self):
        question='乙公司未经甲公司同意转委托个人信息。'
        claim={**self.claim,'statement':'乙公司未经甲公司同意转委托个人信息，违反转委托限制。'}
        for quote,expected in [('题设没有的虚构授权事实',0),(question,1)]:
            verdict=dict(checks=[dict(claim_id='K4',verdict='supported',reason='法律支持',fact_verdict='grounded',fact_reason='题设明确',fact_quotes=[quote])],queries=[])
            with patch('research_engine.complete',return_value=(json.dumps(verdict,ensure_ascii=False),'fixture')):
                check=validate_claims([claim],self.result['evidence'],Budget(),question=question)
            self.assertEqual(check['accepted'],expected)

    def test_engine_retains_rejection_and_only_publishes_repaired_condition(self):
        plan=dict(issues=[dict(id='I4',question='个人信息转委托要求',query='个人信息转委托')],missing_facts=['是否取得同意'])
        good={**self.claim,'statement':'若经查明乙公司未经甲公司同意转委托个人信息，则可能违反转委托限制；是否取得同意目前尚未确认。'}
        assessment=dict(coverage=[dict(issue_id='I4',sufficient=True,reason='法律充分')],sufficient=True,queries=[],missing_facts=['是否取得同意'])
        verdict=dict(checks=[dict(claim_id='R1',verdict='supported',reason='法律支持',fact_verdict='conditional',fact_reason='未将同意未知变成事实')],queries=[])
        repaired=dict(report_version=2,facts=[],claims=[dict(good,role='conclusion')])
        with patch.object(engine,'make_plan',return_value=plan),patch.object(engine,'assess',return_value=assessment),patch.object(engine,'retrieve',return_value=self.result['evidence']),patch.object(engine,'draft',return_value=dict(claims=[self.claim],limitations=[])),patch.object(engine,'complete',side_effect=[(json.dumps(v,ensure_ascii=False),'fixture') for v in (repaired,verdict)]),patch.object(engine,'public_config',return_value=dict(text_model='fixture')):
            result=engine.research(self.job['question'])
        self.assertNotIn(self.claim['statement'],result['report'])
        self.assertIn(good['statement'],result['report'])
        rejected=[c for e in result['events'] for c in e.get('checks',[]) if c.get('fact_status')=='unestablished']
        self.assertTrue(rejected)

if __name__=='__main__':unittest.main()
