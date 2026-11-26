import json
import re
import unittest
from unittest.mock import patch
from corpus import DATA, library, search, stats
from ingest import cn_number, extract_articles
from server import verify, research
from vectors import retrieve_lexical


class CorpusTests(unittest.TestCase):
    def setUp(self):
        p=patch.dict('os.environ',{'LEGAL_RULE_DEMO':'1'}); p.start(); self.addCleanup(p.stop)
    def test_inventory(self):
        expected=json.loads((DATA/'gap185-import-manifest.json').read_text(encoding='utf-8'))['after']
        self.assertEqual(stats(),expected)

    def test_article_integrity(self):
        laws=json.loads((DATA/'laws.json').read_text(encoding='utf-8'))
        self.assertEqual(len({d['id'] for d in laws}),1329)
        for d in laws:
            self.assertNotIn('\ufffd',d['text'])
            self.assertNotIn('???',d['title'])
            self.assertTrue(d['source_sha256'])
            self.assertIn('court.gov.cn',d['url'])
        self.assertTrue(any(d['id']=='E585' and '违约金' in d['text'] for d in laws))

    def test_text_matches_archived_source(self):
        laws=json.loads((DATA/'laws.json').read_text(encoding='utf-8'))
        for filename,offset in [('civil-code.html',0),('contract-interpretation.html',10000)]:
            articles=extract_articles((DATA/'raw'/filename).read_text(encoding='utf-8'))
            for d in laws:
                n=int(d['id'][1:])-offset
                if (offset==0 and int(d['id'][1:])<10000) or (offset==10000 and int(d['id'][1:])>10000):
                    self.assertTrue(articles[n].startswith(d['text']))

    def test_case_filter_and_metadata(self):
        result=library('隆昌伟业','case')
        self.assertEqual(result['total'],1)
        self.assertEqual(result['items'][0]['guiding_number'],'指导案例166号')
        self.assertTrue(result['items'][0]['historical_law_note'])

    def test_pagination(self):
        first=library(page=1); second=library(page=2)
        self.assertEqual(first['total'],json.loads((DATA/'gap185-import-manifest.json').read_text(encoding='utf-8'))['after']['laws'])
        self.assertEqual(len(first['items']),20)
        self.assertTrue({d['id'] for d in first['items']}.isdisjoint(d['id'] for d in second['items']))

    def test_research_has_both_sources(self):
        result=research('合同违约金过高，可以调整吗？')
        self.assertEqual({d['doc_type'] for d in result['evidence']},{'law','case'})
        self.assertEqual(result['verification']['invalid'],[])
        self.assertTrue(any(k.startswith('C') for k in result['verification']['cited']))

    def test_unknown_case_citation(self):
        self.assertEqual(verify('案例 [C99]',[])['invalid'],['C99'])

    def test_chinese_number(self):
        self.assertEqual(cn_number('一千零一'),1001)
        self.assertEqual(cn_number('六十九'),69)

    def test_full_civil_code_no_missing_articles_or_footer(self):
        laws=json.loads((DATA/'laws.json').read_text(encoding='utf-8'))
        civil=[d for d in laws if d['law_name']=='中华人民共和国民法典']
        self.assertEqual({int(d['article']) for d in civil},set(range(1,1261)))
        self.assertTrue(all('责任编辑' not in d['text'] for d in civil))
        self.assertEqual(next(d for d in civil if d['id']=='E1079')['topic'],'婚姻家庭')

    def test_civil_topics_are_searchable(self):
        result=library('离婚','law',topic='婚姻家庭')
        self.assertGreater(result['total'],0)
        self.assertTrue(all(d['topic']=='婚姻家庭' for d in result['items']))
        self.assertTrue(search('夫妻离婚子女抚养'))

    def test_degraded_lexical_retrieval_keeps_exact_bounded_spans(self):
        result=retrieve_lexical('和解后解除保全又恶意违约，要求减少违约金')
        self.assertTrue(result)
        for doc in result:
            self.assertLessEqual(len(doc['text']),1800)
            self.assertIn('BM25',doc['retrieval'])
            self.assertNotEqual(doc.get('reference_status'),'not_reference')


if __name__=='__main__': unittest.main()
