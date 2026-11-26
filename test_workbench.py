import base64,copy,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import corpus,matter_store as store
from matter_evidence import prepare_context,reference_error
from report_review import factual_assertion_errors,legal_condition_errors,document_fact_errors,consistency_review
from models import ModelError
from case_research import strategies

class Reply:
 def __init__(self,data):self.data=data
 def ask(self,*args):return copy.deepcopy(self.data)

class StoreTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
  self.db=patch.object(corpus,'DB',p/'test.sqlite3');self.files=patch.object(store,'STORE',p/'files');self.db.start();self.files.start()
 def tearDown(self):self.db.stop();self.files.stop();self.tmp.cleanup()
 def upload(self,m,text='合同约定交付期限为2026-10-01。',name='合同.txt'):
  return store.upload(m['id'],dict(name=name,kind='contract',content_base64=base64.b64encode(text.encode()).decode()))
 def test_isolated_materials_and_frozen_snapshot(self):
  m=store.create(dict(name='合成测试案'));other=store.create(dict(name='另一测试案'));d=self.upload(m)
  self.assertNotIn('storage_path',d);self.assertEqual(self.upload(m)['id'],d['id'])
  with self.assertRaises(ModelError):store.snapshot(other['id'],[d['id']])
  frozen=store.snapshot(m['id']);self.upload(m,'第二份材料正文','补充.txt')
  self.assertEqual(len(frozen['documents']),1);self.assertEqual(len(store.get(m['id'])['documents']),2)
  self.assertTrue(d['spans'][0]['id'].startswith('U'));self.assertIn('段落 1',d['spans'][0]['location'])
 def test_paths_and_bad_inputs_are_rejected(self):
  m=store.create(dict(name='测试'))
  for name in ['../合同.txt','a\\b.txt','x\n.txt']:
   with self.assertRaises(ModelError):self.upload(m,name=name)
  with self.assertRaises(ModelError):store.extract('合同.txt',b'\xff\xfe')
  with self.assertRaises(ModelError):store.extract('合同.docx',b'bad')
 def test_docx_has_paragraph_provenance(self):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>交付期限</w:t></w:r></w:p><w:p><w:r><w:t>补充协议</w:t></w:r></w:p></w:body></w:document>')
  spans=store.extract('示例.docx',b.getvalue());self.assertEqual([s['location'] for s in spans],['段落 1','段落 2'])
 def test_blank_and_encrypted_pdf_not_confirmed_facts(self):
  from pypdf import PdfWriter
  w=PdfWriter();w.add_blank_page(width=200,height=200);b=io.BytesIO();w.write(b)
  self.assertEqual(store.extract('扫描件.pdf',b.getvalue()),[])
  w.encrypt('secret');b=io.BytesIO();w.write(b)
  with self.assertRaises(ModelError):store.extract('加密.pdf',b.getvalue())

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.spans=[dict(id='Utest_1',material_id='test',name='合同.txt',location='段落 1',text='交付期限为2026-10-01。解除通知于2026-11-01寄出。'),dict(id='Utest_2',material_id='test',name='合同.txt',location='段落 2',text='补充协议记载交付期限为2026-10-15。')]
  self.snapshot=dict(name='合成测试',documents=[dict(id='test',name='合同.txt',kind='contract',sha256='x',status='text_extracted_unverified',spans=self.spans)])
 def obs(self,slot,value,i=0):return dict(slot=slot,value=value,span_id=self.spans[i]['id'],material_id='test',quote=self.spans[i]['text'])
 def test_conflicting_dates_remain_unresolved(self):
  c=prepare_context('交付期限',self.snapshot,Reply(dict(observations=[self.obs('delivery_deadline','2026-10-01'),self.obs('delivery_deadline','2026-10-15',1)])))
  self.assertEqual(c['differences'][0]['status'],'unresolved');self.assertTrue(all(o['disputed'] and not o['independently_verified'] for o in c['observations']))
 def test_posting_not_arrival_and_invented_values_rejected(self):
  c=prepare_context('解除',self.snapshot,Reply(dict(observations=[self.obs('notice_arrival','2026-11-01'),self.obs('delivery_deadline','2026-12-31'),self.obs('substitute_transaction','no')])))
  self.assertEqual(c['observations'],[]);self.assertEqual(len(c['rejected_observations']),3)
 def test_mention_of_missing_receipt_cannot_pass_arrival_gate(self):
  o=self.obs('notice_arrival','2026-11-01寄出，未提供签收记录')
  o['quote']='解除通知于2026-11-01寄出，未提供签收记录。'
  self.spans[0]['text']+='解除通知于2026-11-01寄出，未提供签收记录。'
  c=prepare_context('解除',self.snapshot,Reply(dict(observations=[o])))
  self.assertEqual(c['observations'],[]);self.assertEqual(len(c['rejected_observations']),1)
  from matter_evidence import positive_arrival_record
  self.assertTrue(positive_arrival_record('虽未提供快递签收，但对方邮件确认已收到通知。'))
 def test_material_reference_is_scoped_and_verbatim(self):
  c=dict(material_spans=self.spans)
  self.assertIsNone(reference_error(dict(span_id='Utest_1',quote='交付期限为2026-10-01'),c))
  self.assertTrue(reference_error(dict(span_id='Uother_1',quote='交付期限'),c))
  self.assertTrue(reference_error(dict(span_id='Utest_1',material_id='other',quote='交付期限'),c))
  self.assertTrue(reference_error(dict(span_id='Utest_1',quote='合同已经合法解除'),c))
 def test_document_based_is_not_independent_fact(self):
  ref=dict(span_id='Utest_1',material_id='test',quote='交付期限为2026-10-01')
  c=dict(material_spans=self.spans,observations=[dict(span_id='Utest_1',disputed=True)])
  self.assertTrue(document_fact_errors('本案交付期限已经查明。',[ref],c))
  self.assertTrue(document_fact_errors('合同记载交付期限为2026-10-01。',[ref],c))
  self.assertFalse(document_fact_errors('合同记载交付期限为2026-10-01，但存在差异待核。',[ref],c))

class ReviewTests(unittest.TestCase):
 def test_case_fragments_are_not_counted_as_distinct_cases(self):
  from report_document import quality
  checks=[dict(status='supported',role='case_comparison',case_source_id='C1_1'),dict(status='supported',role='case_comparison',case_source_id='C1_2')]
  q=quality(dict(issues=[]),dict(checks=checks),[dict(id='C1_1',doc_type='case',parent_id='C1'),dict(id='C1_2',doc_type='case',parent_id='C1')])
  self.assertEqual(q['distinct_cases'],1);self.assertEqual(q['case_comparisons'],2)
 def test_later_conditional_does_not_cure_unknown_fact(self):
  text='某石材案与本案相似，均为买卖违约未实施替代交易。若未实施替代交易，可以参考其计算方法。'
  self.assertTrue(factual_assertion_errors(text,'供应商逾期交付设备'))
  self.assertFalse(factual_assertion_errors('若本案买方未实施替代交易，应另核可得利益。','供应商逾期交付设备'))
 def test_summary_must_retain_confirmation_condition(self):
  for role in ['conclusion','rule','action','strategy']:
   c=dict(role=role,statement='直接起诉解除合同的，起诉状副本送达时解除。',references=[])
   self.assertTrue(legal_condition_errors(c,{}))
   c['statement']='直接起诉解除合同，法院确认主张的，起诉状副本送达时解除。';self.assertFalse(legal_condition_errors(c,{}))
 def test_user_statement_cannot_be_inverted_or_inferred_from_question(self):
  self.assertTrue(factual_assertion_errors('本案买方未实施替代交易。','买方已实施替代交易。'))
  self.assertFalse(factual_assertion_errors('本案买方未实施替代交易。','买方未实施替代交易。'))
  self.assertTrue(factual_assertion_errors('本案买方未实施替代交易。','买方是否未实施替代交易？'))
 def test_notice_rule_cannot_replace_termination_basis(self):
  c=dict(statement='迟延履行主要债务，经催告后在合理期限内仍未履行可以解除。',references=[dict(source_id='E565')])
  self.assertTrue(legal_condition_errors(c,dict(E565=dict(text='通知到达时解除合同'))))
  c['references']=[dict(source_id='E563')];self.assertFalse(legal_condition_errors(c,dict(E563=dict(text='主要债务，经催告后在合理期限内仍未履行'))))
 def test_review_only_demotes_real_quotes(self):
  rows=[dict(claim_id='K1',status='supported',statement='本案替代交易情况尚待核实。',references=[]),dict(claim_id='K2',status='unsupported',statement='另一项错误陈述。',references=[])]
  flags=[dict(claim_id='K1',quote='不存在的引文',kind='unknown_fact',reason='无效'),dict(claim_id='K2',quote='另一项错误',kind='unknown_fact',reason='不得提升')]
  r=consistency_review('',{}, {},dict(checks=rows),Reply(dict(flags=flags)))
  self.assertEqual([c['status'] for c in r['checks']],['supported','unsupported'])
  flags=[dict(claim_id='K1',quote='本案替代交易',kind='unknown_fact',reason='测试问题')]
  r=consistency_review('',{}, {},dict(checks=rows),Reply(dict(flags=flags)));self.assertEqual(r['checks'][0]['status'],'uncertain')
 def test_real_model_review_cannot_treat_missing_receipt_as_negative_fact(self):
  checks=[dict(claim_id='K1',status='supported',statement='本案待查明是否实施替代交易。',references=[]),dict(claim_id='K2',status='supported',statement='若未发通知直接起诉或仲裁，法院或仲裁机构确认主张的，合同自副本送达时解除。',references=[])]
  flags=[dict(claim_id='K1',quote='本案待查明是否实施替代交易',kind='unknown_fact',reason='未提交凭证，应直接认定本案未实施替代交易。'),dict(claim_id='K2',quote=checks[1]['statement'],kind='condition_missing',reason='遗漏是否已送达的事实条件。')]
  r=consistency_review('',{}, {},dict(checks=checks),Reply(dict(flags=flags)))
  self.assertEqual(r['accepted'],2);self.assertEqual(len(r['consistency_review']['rejected_flags']),2)
 def test_unconfirmed_goal_cannot_publish_recommendation(self):
  data=dict(report_version=2,facts=[],claims=[dict(issue_id='I1',role='recommendation',option_key='termination',statement='若符合解除条件，建议解除，否则重新核对方案。',references=[dict(source_id='E1',quote='真实法条连续原文')])])
  result=dict(question='设备交付合同',research_plan=dict(issues=[dict(id='I1',title='解除')]),verification=dict(checks=[]),evidence=[],assessment={})
  with patch('case_research.validate_claims',return_value=dict(checks=[],passed=False)) as validate:
   strategies(result,dict(goal='undecided'),Reply(data));self.assertEqual(validate.call_args.args[0],[])

if __name__=='__main__':unittest.main()
