import json
import unittest
from unittest.mock import patch
import research_engine as engine
from models import ModelError,ModelServiceError

D1=dict(id='E563',doc_type='law',title='合同解除',text='当事人一方迟延履行主要债务，经催告后在合理期限内仍未履行。')
D2=dict(id='E585',doc_type='law',title='违约金',text='约定的违约金过分高于造成的损失的，可以请求适当减少。')
REF=dict(source_id='E563',quote='经催告后在合理期限内仍未履行')
PLAN=dict(issues=[dict(id='I1',question='是否可以解除合同',query='合同解除催告')],missing_facts=['催告送达情况'])
GOOD=dict(coverage=[dict(issue_id='I1',sufficient=True,reason='有相关规则',references=[REF])],queries=[],missing_facts=[])
BAD=dict(coverage=[dict(issue_id='I1',sufficient=False,reason='缺少违约金规则',references=[])],queries=['违约金调整'],missing_facts=[])
CLAIM=dict(id='K1',issue_id='I1',statement='需要核对催告后是否仍未履行主要债务。',references=[REF])
ROLES=('conclusion','application','supporting','counterargument','action')
UNITS=[dict(CLAIM,id='K'+str(i+1),role=role) for i,role in enumerate(ROLES)]
DRAFT=dict(report_version=2,facts=[],claims=UNITS,limitations=[])
SUPPORTED=dict(checks=[dict(claim_id=c['id'],verdict='supported',reason='来源支持该条件性表述',fact_verdict='conditional',fact_reason='仅说明需核对催告条件，未认定个案事实') for c in UNITS],queries=[])


class EngineTests(unittest.TestCase):
    def session(self,outputs):
        # These fixtures exercise the pre-existing retrieval/claim flow; v3 seams
        # have their own integration test with real notice and ledger checks.
        p=patch.object(engine,'requires_notice',return_value=False);p.start();self.addCleanup(p.stop)
        p=patch.object(engine,'make_ledger',side_effect=lambda q,p,b:dict(facts=[dict(status='unknown',text='是否提供合同？')],materials=[dict(id='M'+str(n),name='合同资料',issue_id=i['id'],element='other',question='是否提供合同？',claim_roles=['application'],status='not_submitted') for n,i in enumerate(p['issues'],1)]));p.start();self.addCleanup(p.stop)
        p=patch.object(engine,'complete',side_effect=[(json.dumps(v,ensure_ascii=False),'fixture') for v in outputs]);p.start();self.addCleanup(p.stop)
        p=patch.object(engine,'public_config',return_value={'text_model':'fixture'});p.start();self.addCleanup(p.stop)

    def test_supplement_adds_evidence_and_reassesses(self):
        self.session([PLAN,BAD,GOOD,DRAFT,SUPPORTED])
        with patch.object(engine,'retrieve',side_effect=[[D1],[D2]]) as retrieve:
            r=engine.research('合同解除与违约金')
        self.assertEqual(retrieve.call_count,2)
        self.assertEqual(r['supplement_rounds'],1)
        self.assertEqual(r['budget']['model_calls'],5)
        self.assertEqual(r['outcome'],'complete')
        self.assertEqual(r['verification']['accepted'],5)

    def test_embedding_failure_degrades_once_and_preserves_real_research(self):
        plan=dict(issues=[dict(id='I1',question='解除',query='解除'),dict(id='I2',question='违约金',query='违约金')],missing_facts=[])
        assessment=dict(sufficient=True,coverage=[dict(issue_id='I1',sufficient=True,reason='covered')],missing_facts=[],queries=[])
        self.session([SUPPORTED,SUPPORTED])
        p=patch.object(engine,'draft',return_value={**DRAFT,'limitations':[]});p.start();self.addCleanup(p.stop)
        p=patch.object(engine,'repair_verified',side_effect=lambda q,p,e,a,v,b:v);p.start();self.addCleanup(p.stop)
        with patch.object(engine,'make_plan',return_value=plan),patch.object(engine,'assess',return_value=assessment),patch.object(engine,'retrieve',side_effect=ModelServiceError('tls','embedding',3,True)) as vector,patch.object(engine,'retrieve_lexical',return_value=[D1]) as lexical:
            result=engine.research('解除与违约金')
        self.assertEqual(vector.call_count,1);self.assertEqual(lexical.call_count,2)
        self.assertEqual(result['retrieval_mode'],'bm25_fallback')
        self.assertTrue(result['report'].startswith('## 检索降级提示'))
        self.assertEqual(result['verification']['accepted'],5)

    def test_auth_and_index_errors_never_degrade(self):
        self.session([PLAN])
        for fault in [ModelServiceError('http','embedding',1,False,401),ModelError('stale index')]:
            with patch.object(engine,'make_plan',return_value=PLAN),patch.object(engine,'retrieve',side_effect=fault),patch.object(engine,'retrieve_lexical') as lexical:
                with self.assertRaises(ModelError):engine.research('解除')
            lexical.assert_not_called()

    def test_mid_job_degradation_retains_prior_hybrid_evidence(self):
        plan=dict(issues=[dict(id='I1',question='解除',query='解除'),dict(id='I2',question='违约金',query='违约金')],missing_facts=[])
        assessment=dict(sufficient=True,coverage=[],missing_facts=[],queries=[])
        self.session([SUPPORTED,SUPPORTED])
        p=patch.object(engine,'draft',return_value={**DRAFT,'limitations':[]});p.start();self.addCleanup(p.stop)
        p=patch.object(engine,'repair_verified',side_effect=lambda q,p,e,a,v,b:v);p.start();self.addCleanup(p.stop)
        with patch.object(engine,'make_plan',return_value=plan),patch.object(engine,'assess',return_value=assessment),patch.object(engine,'retrieve',side_effect=[[D1],ModelServiceError('tls','embedding',3,True)]),patch.object(engine,'retrieve_lexical',return_value=[D2]):
            result=engine.research('解除与违约金')
        self.assertEqual({d['id'] for d in result['evidence']},{'E563','E585'})
        self.assertIn('此前成功的混合检索证据仍保留',result['report'])
        self.assertNotIn('仅使用本地 BM25',result['report'])

    def test_gap_without_model_queries_uses_issue_question(self):
        self.session([PLAN,{**BAD,'queries':[]},GOOD,DRAFT,SUPPORTED])
        with patch.object(engine,'retrieve',side_effect=[[D1],[D2]]) as retrieve:
            result=engine.research('合同解除与违约金')
        self.assertEqual(retrieve.call_args_list[1].args[0],PLAN['issues'][0]['question'])
        self.assertEqual(result['supplement_rounds'],1)
        self.assertIn('E585',{d['id'] for d in result['evidence']})

    def test_no_new_documents_stops_retrieval(self):
        self.session([PLAN,BAD,DRAFT,SUPPORTED])
        with patch.object(engine,'retrieve',side_effect=[[D1],[D1]]) as retrieve:
            r=engine.research('合同解除')
        self.assertEqual(retrieve.call_count,2)
        self.assertEqual(r['outcome'],'limited')

    def test_four_issue_initial_pool_preserves_supplement(self):
        plan=dict(issues=[dict(id='I'+str(i),question='争点'+str(i),query='初检'+str(i)) for i in range(1,5)],missing_facts=[])
        good=dict(coverage=[dict(issue_id=i['id'],sufficient=True,reason='已覆盖',references=[REF]) for i in plan['issues']],queries=[],missing_facts=[])
        bad={**good,'coverage':[{**good['coverage'][0],'sufficient':False}]+good['coverage'][1:],'queries':['新增法律依据']}
        docs=[dict(D1,id='E'+str(563+i)) for i in range(24)]
        extra=dict(D2,id='E9999')
        self.session([plan,SUPPORTED,SUPPORTED])
        p=patch.object(engine,'draft',return_value={**DRAFT,'limitations':[]});p.start();self.addCleanup(p.stop)
        p=patch.object(engine,'repair_verified',side_effect=lambda q,p,e,a,v,b:v);p.start();self.addCleanup(p.stop)
        with patch.object(engine,'assess',side_effect=[dict(bad,sufficient=False),dict(good,sufficient=True)]), patch.object(engine,'retrieve',side_effect=[docs[i:i+6] for i in range(0,24,6)]+[[extra]]):
            result=engine.research('四争点复杂问题')
        self.assertIn('E9999',{d['id'] for d in result['evidence']})
        self.assertEqual(sum(e['stage_key']=='assess' and e['state']=='completed' and 'coverage' in e for e in result['events']),2)

    def test_supplement_round_limit(self):
        bad2={**BAD,'queries':['违约金损失计算']}
        self.session([PLAN,BAD,bad2,BAD,DRAFT,SUPPORTED])
        third={**D2,'id':'E584'}
        with patch.object(engine,'retrieve',side_effect=[[D1],[D2],[third]]) as retrieve:
            r=engine.research('合同解除')
        self.assertEqual(r['supplement_rounds'],2)
        self.assertEqual(retrieve.call_count,3)
        self.assertEqual(r['outcome'],'limited')

    def test_invalid_quote_never_reaches_semantic_validator(self):
        claim={**CLAIM,'references':[dict(source_id='E563',quote='这是一个并不存在的法律原文片段')]}
        with patch.object(engine,'complete') as complete:
            result=engine.validate_claims([claim],[D1],engine.Budget())
        complete.assert_not_called()
        self.assertEqual(result['accepted'],0)

    def test_inline_unknown_citation_rejected(self):
        claim={**CLAIM,'statement':'结论 [E999]'}
        check=engine.validate_claims([claim],[D1],engine.Budget())
        self.assertFalse(check['passed'])

    def test_false_positive_coverage_needs_actual_quote(self):
        self.session([{**GOOD,'coverage':[{**GOOD['coverage'][0],'references':[]}]}])
        self.assertFalse(engine.assess('合同',PLAN,[D1],engine.Budget())['sufficient'])

    def test_missing_semantic_verdict_is_uncertain(self):
        self.session([dict(checks=[],queries=[])])
        check=engine.validate_claims([CLAIM],[D1],engine.Budget())
        self.assertEqual(check['checks'][0]['status'],'uncertain')

    def test_validator_receives_original_facts_and_coverage_gaps(self):
        question='未查验公告，不代表未披露'
        with patch.object(engine,'complete',return_value=(json.dumps(SUPPORTED,ensure_ascii=False),'fixture')) as complete:
            engine.validate_claims([CLAIM],[D1],engine.Budget(),question=question,assessment=BAD)
        sent=json.loads(complete.call_args.args[1])
        self.assertEqual(sent['question'],question)
        self.assertEqual(sent['assessment'],BAD)

    def test_unsupported_claim_not_published_and_repaired(self):
        unsupported=dict(checks=[dict(claim_id='K1',verdict='unsupported',reason='适用条件不足')],queries=[])
        self.session([PLAN,GOOD,DRAFT,unsupported,DRAFT,unsupported])
        with patch.object(engine,'retrieve',return_value=[D1]):r=engine.research('合同解除')
        self.assertNotIn(CLAIM['statement'],r['report'])
        self.assertEqual(r['verification']['accepted'],0)
        self.assertEqual(r['outcome'],'limited')

    def test_budget_prevents_network(self):
        with patch.object(engine,'complete') as complete:
            with self.assertRaises(engine.ResearchStopped):engine.Budget(max_calls=0).ask('x',{},10)
        complete.assert_not_called()

    def test_cancel_prevents_calls(self):
        with patch.object(engine,'complete') as complete:
            with self.assertRaises(engine.ResearchCancelled):engine.research('合同',cancelled=lambda:True)
        complete.assert_not_called()

    def test_invalid_json_rejected(self):
        with self.assertRaises(ModelError):engine.parse_json('not json')

    def test_unverified_limitations_never_become_report_conclusions(self):
        text=engine.render(PLAN,{},dict(checks=[]),['必须赔偿一百万元'], '预算已用尽')
        self.assertNotIn('必须赔偿一百万元',text)

    def test_original_question_omission_blocks_full_coverage(self):
        self.session([{**GOOD,'uncovered_questions':['未处理解除后的赔偿请求']}])
        self.assertFalse(engine.assess('解除及赔偿',PLAN,[D1],engine.Budget())['sufficient'])

    def test_verification_supplement_reassesses_coverage(self):
        unsupported=dict(checks=[dict(claim_id='K1',verdict='unsupported',reason='缺依据')],queries=['损失赔偿范围'])
        initial=GOOD
        repaired={**SUPPORTED,'checks':[{**c,'claim_id':'R'+str(i+1)} for i,c in enumerate(SUPPORTED['checks'])]}
        self.session([PLAN,initial,DRAFT,unsupported,GOOD,DRAFT,repaired])
        with patch.object(engine,'retrieve',side_effect=[[D1],[D2]]):r=engine.research('合同解除')
        self.assertTrue(r['assessment']['sufficient'])
        self.assertEqual(r['outcome'],'complete')

    def test_empty_pool_cannot_produce_report_claims(self):
        self.session([PLAN,{**BAD,'queries':[]}])
        with patch.object(engine,'retrieve',return_value=[]):r=engine.research('合同解除')
        self.assertEqual(r['evidence'],[])
        self.assertEqual(r['outcome'],'limited')
        self.assertIn('证据不足',r['report'])


if __name__=='__main__':unittest.main()
