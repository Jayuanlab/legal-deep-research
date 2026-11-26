import json,unittest
from unittest.mock import patch
import corpus
from law_validity import classify,enrich,load_rules
class LawValidityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.source=json.loads((corpus.DATA/'law-validity-repeal-source.json').read_text(encoding='utf-8'))
 def test_exact_title_and_issue_both_required(self):
  row=next(r for r in self.source['rows'] if '法释〔2009〕5号' in r[2])
  d=dict(id='x',doc_type='law',law_name=row[1],version='法释〔2009〕5号')
  self.assertEqual(classify(d,self.source)['code'],'repealed')
  d['version']='法释〔2025〕5号'
  self.assertEqual(classify(d,self.source)['code'],'needs_review')
  d['law_name']='最高人民法院关于适用《中华人民共和国合同法》若干问题的解释（三）'
  self.assertIsNone(classify(d,self.source))
 def test_only_the_repealed_clause_is_labelled(self):
  d=corpus.library('领取退休金','law')['items']
  old=next(d for d in d if d['id']=='E27032')
  self.assertEqual(old['validity']['code'],'partially_repealed')
  self.assertIn('仅本条第一款',old['validity']['scope'])
  others=corpus.library('最高人民法院关于审理劳动争议案件适用法律问题的解释（一）','law',size=60)['items']
  self.assertTrue(all(x.get('validity',{}).get('code')!='partially_repealed' for x in others if x['id']!='E27032'))
 def test_repealed_records_stay_browsable_but_not_retrievable(self):
  rows=corpus.library(validity='repealed',size=200)
  self.assertEqual(rows['total'],json.loads((corpus.DATA/'validity-all-report.json').read_text(encoding='utf-8'))['counts']['repealed'])
  self.assertTrue(all(d['reference_status']=='not_reference' for d in rows['items']))
  ids={d['id'] for d in rows['items']}
  self.assertFalse(ids&{d['id'] for d in corpus.search('合同法 婚姻法 劳动争议 物权法',1000,'law')})
 def test_pending_and_future_not_mislabelled_as_repealed(self):
  pending=corpus.library(validity='needs_review')['items']
  self.assertTrue(pending);self.assertTrue(all(d['validity']['code']!='repealed' for d in pending))
  future=corpus.library(validity='not_yet_effective')['items']
  self.assertTrue(future);self.assertTrue(all(d['validity']['code']=='not_yet_effective' for d in future))
 def test_overlay_survives_rebuild_without_changing_text_hash(self):
  rules=load_rules();key=next(k for k,v in rules.items() if v['code']=='repealed')
  d=dict(id=key,doc_type='law',title='原始标题',text='原始正文',text_sha256=rules[key]['document_text_sha256'],source_sha256=rules[key]['document_source_sha256'],version=rules[key]['document_version'])
  result=enrich(d,rules)
  self.assertEqual(result['text'],d['text']);self.assertEqual(result['text_sha256'],d['text_sha256'])
  self.assertEqual(result['reference_status'],'not_reference');self.assertNotIn('validity',d)
 def test_invalid_status_filter_rejected(self):
  with self.assertRaises(ValueError):corpus.library(validity='made_up')
  with self.assertRaises(ValueError):corpus.library(doc_type='case',validity='repealed')
if __name__=='__main__':unittest.main()
