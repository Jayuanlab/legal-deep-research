import json,re,unittest
from pathlib import Path
from unittest.mock import patch
from official_bulk import ROOT,RAW,allowed
from collect_npc_texts import split_articles
from parse_court_bulk import body
from server import verify

class BulkSourceTests(unittest.TestCase):
    def test_article_insertions_and_missing_numbers(self):
        parts=split_articles('第一条 总则。\n第二条 规则。\n第二条之一 增补。\n第三条 施行。')
        self.assertEqual([n for n,t in parts],['1','2','2之1','3'])
        for text in ('第一条 规则。\n第三条 缺号。','第一条 原文。\n第一条 另一版本。'):
            with self.assertRaises(ValueError):split_articles(text)

    def test_public_hosts_and_https_boundary(self):
        self.assertTrue(allowed('https://xzfg.moj.gov.cn/front/law/detail?LawID=570'))
        self.assertFalse(allowed('https://court.gov.cn.evil.example/a'))
        self.assertFalse(allowed('http://www.court.gov.cn/a'))

    def test_bulk_cases_have_exact_source_spans_and_correct_type(self):
        docs=json.loads((ROOT/'data/cases-bulk.json').read_text(encoding='utf-8'))
        records=json.loads((ROOT/'data/court-collection-typical-cases.json').read_text(encoding='utf-8'))['items']
        records={x['url']:x for x in records};texts={}
        self.assertGreater(len(docs),1800)
        for d in docs:
            if d['url'] not in texts:texts[d['url']]=body(records[d['url']])[0]
            self.assertEqual(d['text'],texts[d['url']][d['source_start']:d['source_end']])
            self.assertNotIn('guiding_number',d)
            self.assertIn('非指导案例',d['kind'])
            self.assertTrue(d['facts'])

    def test_all_279_guides_present_and_republication_not_forged(self):
        docs=json.loads((ROOT/'data/cases.json').read_text(encoding='utf-8'))+json.loads((ROOT/'data/cases-guiding-extra.json').read_text(encoding='utf-8'))
        self.assertEqual({d['guiding_id'] for d in docs},set(range(1,280)))
        guide=next(d for d in docs if d['guiding_id']==45)
        self.assertIn('sdcourt.gov.cn',guide['url']);self.assertIn('转载',guide['kind'])
        self.assertEqual(guide['date'],'2015-04-15')

    def test_unsegmented_text_never_gets_fictional_article_number(self):
        docs=json.loads((ROOT/'data/laws-regulations.json').read_text(encoding='utf-8'))
        full=[d for d in docs if d['article'] is None]
        self.assertEqual(len(full),24)
        self.assertTrue(all('全文未分条' in d['kind'] and '（全文）' in d['title'] for d in full))

    def test_future_sources_explicitly_excluded(self):
        docs=json.loads((ROOT/'data/laws-regulations.json').read_text(encoding='utf-8'))
        future=[d for d in docs if d.get('date') and d['date']>'2026-11-12']
        self.assertTrue(future)
        self.assertTrue(all(d.get('reference_status')=='not_reference' and '尚未施行' in d['authority_status'] for d in future))

    def test_coverage_does_not_count_a_catalog_as_full_text(self):
        c=json.loads((ROOT/'data/national-coverage.json').read_text(encoding='utf-8'))
        self.assertEqual(c['parsed_names'],303)
        self.assertEqual(c['missing_names'],[])
        self.assertEqual(c['title_matches'],303)
        self.assertEqual(len(json.loads((ROOT/'data/gap185-targets.json').read_text(encoding='utf-8'))),185)
        self.assertFalse(c['npc_catalog']['complete'])
        self.assertEqual(c['npc_catalog']['full_texts'],0)

    def test_new_source_ids_participate_in_legacy_reference_check(self):
        ids=['R0123456789abcdef0123A10','CT508031N2','J443891A23','T20006']
        r=verify(' '.join('['+x+']' for x in ids),[dict(id=x) for x in ids])
        self.assertEqual(set(r['cited']),set(ids));self.assertEqual(r['invalid'],[])

if __name__=='__main__':unittest.main()
