import json,unittest
from corpus import DATA,library,search
from collect_expansion import LAW_SOURCES,CASE_SOURCES,archive,law_articles,case_records

class ExpansionCollectionTests(unittest.TestCase):
    def test_all_articles_match_archives_and_keep_final_paragraphs(self):
        docs=json.loads((DATA/'laws-expansion.json').read_text(encoding='utf-8'))
        self.assertEqual(len(docs),468)
        for s in LAW_SOURCES:
            _,_,text,_=archive(s['key']);original=law_articles(s,text)
            rows=[d for d in docs if d['law_name']==s['name']]
            self.assertEqual([int(d['article']) for d in rows],list(range(1,s['count']+1)))
            self.assertTrue(all(d['text']==original[int(d['article'])] for d in rows))
            self.assertTrue(rows[-1]['text'].endswith(s['tail']))

    def test_cases_are_body_spans_not_directory_entries(self):
        docs=json.loads((DATA/'cases-extra.json').read_text(encoding='utf-8'))
        self.assertEqual(len(docs),41)
        for s in CASE_SOURCES:
            _,_,text,_=archive(s['key']);parsed=case_records(s,text)
            rows=[d for d in docs if d['source_collection']==s['key']]
            self.assertEqual(len(rows),s['count'])
            for d,p in zip(rows,parsed):
                self.assertEqual(d['text'],text[d['source_start']:d['source_end']])
                self.assertEqual(d['text'],p['text'])
                self.assertNotIn('guiding_number',d)
                self.assertIn('非指导案例',d['kind'])
                self.assertTrue(d['points'])

    def test_repealed_labor_paragraph_kept_but_excluded(self):
        docs=json.loads((DATA/'laws-expansion.json').read_text(encoding='utf-8'))
        old=next(d for d in docs if d['id']=='E27032')
        self.assertIn('第一款',old['authority_status'])
        self.assertIn('其余款未',old['authority_status'])
        self.assertEqual(old['reference_status'],'not_reference')
        self.assertIn('E27032',[d['id'] for d in library('领取退休金','law')['items']])
        self.assertNotIn('E27032',[d['id'] for d in search('领取退休金 养老保险待遇 劳务关系',1000,'law')])

if __name__=='__main__':unittest.main()
