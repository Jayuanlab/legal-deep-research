import hashlib,json,unittest
from urllib.parse import urlparse
from pathlib import Path
from unittest.mock import patch
from collect_gap185 import ROOT,parse_candidate,read_source,OUT,digest

class Gap185Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.targets=json.loads((ROOT/'data/gap185-targets.json').read_text(encoding='utf-8'))
  cls.docs=json.loads((ROOT/'data/laws-gap185.json').read_text(encoding='utf-8'))
 def test_all_frozen_targets_have_source_body_and_original_bytes(self):
  self.assertEqual({d['law_name'] for d in self.docs},{t['name'] for t in self.targets})
  for t in self.targets:
   r=json.loads((OUT/f"parsed/{digest(t['name'])}.json").read_text(encoding='utf-8'))
   self.assertTrue(r['parts'])
   self.assertEqual(hashlib.sha256((ROOT/'data'/r['raw_path']).read_bytes()).hexdigest(),r['source_sha256'])
   host=urlparse(r['url']).hostname
   self.assertTrue(host.endswith('.gov.cn') or host=='www.12371.cn')
 def test_law_not_implementing_regulation(self):
  for name,count in [('中华人民共和国民族区域自治法',74),('中华人民共和国反外国制裁法',16)]:
   ds=[d for d in self.docs if d['law_name']==name]
   self.assertEqual(len(ds),count)
   self.assertTrue(all('制定本规定' not in d['text'] for d in ds))
 def test_exact_title_locates_the_law_before_other_laws_citing_it(self):
  from corpus import library
  for name in ['中华人民共和国学位法','中华人民共和国国籍法','中华人民共和国民族区域自治法']:
   rows=library(name,'law',size=4)['items']
   self.assertTrue(rows)
   self.assertTrue(all(d['law_name']==name for d in rows))
 def test_reject_citation_article_and_catalog_as_whole_law(self):
  for text in ['目录\n全国人民代表大会常务委员会关于示例的决定（1984年通过）\n其他法律目录。',
               '全国人民代表大会常务委员会关于示例的决定\n法院分析认为该决定规定了管辖。']:
   with patch('collect_gap185.read_source',return_value=([(text,True)],{},'fake','法院研究文章')):
    with self.assertRaises(ValueError):parse_candidate(dict(name='全国人民代表大会常务委员会关于示例的决定',source_entry='1984年通过'),'https://example.gov.cn/a')
 def test_retirement_resolution_not_annex_and_excluded_when_status_uncertain(self):
  ds=[d for d in self.docs if '批准《国务院关于工人退休' in d['law_name']]
  self.assertEqual(len(ds),1);self.assertIsNone(ds[0]['article'])
  self.assertEqual(ds[0]['reference_status'],'not_reference')
  self.assertNotIn('第一条',ds[0]['text']);self.assertIn('原则批准',ds[0]['text'])
 def test_whole_decisions_have_operative_text_without_editorial_tail(self):
  for d in self.docs:
   if d['article'] is None:
    self.assertNotIn('来源：中国人大网',d['text'])
    self.assertNotIn('作者：',d['text'])
    self.assertNotIn('发布时间：',d['text'])

if __name__=='__main__':unittest.main()
