import hashlib
import json
import unittest
from corpus import DATA,search
from collect_cases import parse_case
from collect_laws_extra import SOURCES,extract_articles
from vectors import chunks


class CollectionTests(unittest.TestCase):
    def test_extra_laws_continuous_and_unchanged_from_archive(self):
        docs=json.loads((DATA/'laws-extra.json').read_text(encoding='utf-8'))
        manifests=json.loads((DATA/'laws-extra-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(docs),985)
        for source in SOURCES:
            meta=next(x for x in manifests if x['key']==source['key'])
            raw=(DATA.parent/meta['raw_path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),meta['source_sha256'])
            original=extract_articles(raw.decode(meta['encoding']),source)
            rows=[d for d in docs if d['law_name']==source['law_name']]
            self.assertEqual({int(d['article']) for d in rows},set(range(1,source['count']+1)))
            self.assertTrue(all(d['text']==original[int(d['article'])] for d in rows))

    def test_guarantee_special_rules_complete_and_typed(self):
        docs=json.loads((DATA/'laws-extra.json').read_text(encoding='utf-8'))
        rows={d['id']:d for d in docs if d['topic']=='担保'}
        self.assertEqual(len(rows),71)
        self.assertTrue(all(d['kind']=='司法解释原文' and d['date']=='2021-01-01' for d in rows.values()))
        self.assertEqual(rows['E26009']['text'].count('\n'),2)
        self.assertIn('且不承担担保责任或者赔偿责任',rows['E26009']['text'])
        self.assertIn('不适用前款第二项、第三项',rows['E26008']['text'])
        self.assertNotIn('二、关于',rows['E26021']['text'])

    def test_guiding_case_inventory_and_raw_hash(self):
        cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
        self.assertEqual({d['guiding_id'] for d in cases},set(range(1,280))-{45})
        self.assertEqual(len({d['id'] for d in cases}),len(cases))
        for d in cases:
            self.assertEqual(hashlib.sha256((DATA/d['raw_path']).read_bytes()).hexdigest(),d['source_sha256'])
            self.assertEqual(hashlib.sha256(d['text'].encode()).hexdigest(),d['text_sha256'])
            self.assertTrue(d['points']);self.assertTrue(d['holding'])

    def test_old_inline_layout_and_execution_layout(self):
        cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
        for n in (3,7,67,267):
            doc=next(d for d in cases if d['guiding_id']==n)
            parsed=parse_case((DATA/doc['raw_path']).read_bytes(),doc['url'],n,old=doc)
            self.assertEqual(parsed['text'],doc['text'])
            self.assertTrue(parsed['points']);self.assertTrue(parsed['date'])

    def test_withdrawn_records_visible_but_excluded_from_research(self):
        cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
        withdrawn=[d for d in cases if d.get('reference_status')=='not_reference']
        self.assertEqual({d['guiding_id'] for d in withdrawn},{9,20,123,136,139,204})
        result=search('合同 环境污染 公司 指导案例',1000,'case')
        self.assertTrue(result)
        self.assertFalse(any(d.get('reference_status')=='not_reference' for d in result))

    def test_chunk_spans_cover_full_text(self):
        doc=dict(id='C123',title='case',text=('paragraph '*80+'\n')*10)
        parts=chunks(doc);self.assertGreater(len(parts),1)
        positions=set()
        for p in parts:
            self.assertEqual(p['text'],doc['text'][p['start']:p['end']])
            self.assertLessEqual(len(p['text']),1800)
            positions.update(range(p['start'],p['end']))
        self.assertEqual(positions,set(range(len(doc['text']))))
        self.assertEqual(len({p['id'] for p in parts}),len(parts))


if __name__=='__main__':unittest.main()
