import json
import math
import unittest
from pathlib import Path
from evaluation.evaluate import load_dataset,score,canonical,semantic_rank
from evaluation.build_dataset import corpus_fingerprint

class RetrievalEvaluationTests(unittest.TestCase):
    def test_known_recall_and_first_relevant_rank(self):
        qrels=[dict(doc_id='E1',grade=2,evidence_quote='direct'),dict(doc_id='E2',grade=1,evidence_quote='context')]
        ranked=[dict(id='E3',text='unjudged'),dict(id='E2',text='context'),dict(id='E1',text='direct')]
        m=score(ranked,qrels,2)
        self.assertEqual(m['known_recall_at_k'],.5)
        self.assertEqual(m['mrr_at_k'],.5)
        self.assertEqual(m['hit_at_1'],0)
        self.assertAlmostEqual(m['known_ndcg_at_k'],(1/math.log2(3))/(3+1/math.log2(3)))

    def test_parent_deduplication_prevents_double_credit(self):
        ranked=[dict(id='C1_0',parent_id='C1',text='anchor'),dict(id='C1_1',parent_id='C1',text='anchor'),dict(id='C2',text='second')]
        labels=[dict(doc_id='C1',grade=2,evidence_quote='anchor'),dict(doc_id='C2',grade=2,evidence_quote='second')]
        self.assertEqual(score(ranked,labels,2)['known_recall_at_k'],1)
        self.assertEqual(canonical(ranked[0]),'C1')

    def test_passage_anchor_distinct_from_document_hit(self):
        m=score([dict(id='C1_2',parent_id='C1',text='different passage')],[dict(doc_id='C1',grade=2,evidence_quote='gold quote')],2,passage=True)
        self.assertEqual(m['known_recall_at_k'],1)
        self.assertEqual(m['anchor_recall_at_k'],0)

    def test_no_answer_controls_excluded_from_positive_metrics(self):
        self.assertIsNone(score([dict(id='E1',text='unjudged')],[],4))

    def test_dataset_provenance_and_source_disjoint_splits(self):
        rows,manifest,docs=load_dataset(Path(__file__).parent/'evaluation/archives/retrieval-v1',Path(__file__).parent/'evaluation/archives/corpus-before-expansion-20261112.json')
        self.assertEqual(len(rows),80)
        self.assertEqual(manifest['split_counts'],dict(dev=35,test=37,control=8))
        self.assertEqual(sum(r['collection']=='law' and bool(r['qrels']) for r in rows),48)
        self.assertEqual(sum(r['collection']=='case' and bool(r['qrels']) for r in rows),24)
        self.assertTrue(all(r['split']=='dev' for r in rows if r['style']=='locator'))

    def test_v2_expands_sources_and_preserves_fixed_regression_rows(self):
        rows,manifest,docs=load_dataset()
        self.assertEqual(manifest['version'],'retrieval-v2')
        self.assertEqual(len(rows),400)
        self.assertEqual(manifest['cohort_counts'],dict(regression_v1=80,expansion_v2=320))
        self.assertEqual(manifest['unique_qrel_sources'],dict(law=118,case=100))
        old,_,_=load_dataset(Path(__file__).parent/'evaluation/archives/retrieval-v1',Path(__file__).parent/'evaluation/archives/corpus-before-expansion-20261112.json')
        current={r['id']:r for r in rows}
        for original in old:
            for key,value in original.items():
                if key!='version':self.assertEqual(current[original['id']][key],value)
        self.assertEqual(sum(r['collection']=='law' and bool(r['qrels']) for r in rows),200)
        self.assertEqual(sum(r['collection']=='case' and bool(r['qrels']) for r in rows),176)

    def test_v2_controls_cover_all_six_withdrawn_cases(self):
        rows,_,_=load_dataset()
        forbidden={key for r in rows if r['split']=='control' for key in r.get('forbidden_ids',[])}
        self.assertEqual(forbidden,{'C1009','C1020','C1123','C1136','C1139','C1204'})

    def test_expansion_introduces_new_positive_sources_and_unique_queries(self):
        rows,_,_=load_dataset()
        old={q['doc_id'] for r in rows if r['cohort']=='regression_v1' for q in r['qrels']}
        new={q['doc_id'] for r in rows if r['cohort']=='expansion_v2' for q in r['qrels']}
        self.assertFalse(old&new)
        self.assertEqual(len(new),152)
        self.assertEqual(len({r['query'] for r in rows}),400)

    def test_expanded_case_questions_have_query_specific_anchors(self):
        rows,_,_=load_dataset();families={}
        for r in rows:
            if r['collection']=='case' and r['cohort']=='expansion_v2' and r['qrels']:families.setdefault(r['family'],[]).append(r)
        self.assertEqual(len(families),76)
        for pair in families.values():
            self.assertEqual(len(pair),2)
            self.assertNotEqual(pair[0]['qrels'][0]['evidence_quote'],pair[1]['qrels'][0]['evidence_quote'])

    def test_semantic_ranking_uses_best_fragment_per_parent_and_type(self):
        doc=dict(id='C1',doc_type='case',title='case',text='full')
        other=dict(id='C2',doc_type='case',title='other',text='full')
        law=dict(id='E1',doc_type='law',title='law',text='full')
        usable=[(doc,dict(id='C1_0',text='low'),[0,1]),(doc,dict(id='C1_1',text='high'),[1,0]),(other,dict(id='C2',text='other'),[.5,.5]),(law,dict(id='E1',text='law'),[1,0])]
        ranked=semantic_rank([1,0],usable,'case',2)
        self.assertEqual([canonical(d) for d in ranked],['C1','C2'])
        self.assertEqual(ranked[0]['id'],'C1_1')

    def test_fingerprint_covers_ranking_fields_and_filter_status(self):
        doc=dict(id='E1',doc_type='law',title='old title',text='unchanged text',tags='tag',reference_status='unverified')
        original=corpus_fingerprint({'E1':doc})
        for key,value in [('title','new title'),('tags','new tag'),('reference_status','not_reference')]:
            self.assertNotEqual(original,corpus_fingerprint({'E1':dict(doc,**{key:value})}))

if __name__=='__main__':unittest.main()
