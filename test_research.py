import unittest
from unittest.mock import patch
from server import search,verify,research

class ResearchTests(unittest.TestCase):
    def setUp(self):
        p=patch.dict('os.environ',{'LEGAL_RULE_DEMO':'1'}); p.start(); self.addCleanup(p.stop)
    def test_contract_retrieval(self):
        hits=search('违约金过高如何调整')
        self.assertTrue(hits)
        self.assertTrue(any('违约金' in hit['text'] for hit in hits))

    def test_labor_material_available(self):
        result=research('劳动合同违法解除，经济补偿和赔偿金如何计算？')
        self.assertTrue(result['evidence'])
        self.assertTrue(any('劳动' in d.get('law_name','') for d in result['evidence']))

    def test_unknown_citations(self):
        check=verify('依据 [E99]',search('合同解除'))
        self.assertEqual(check['invalid'],['E99'])

    def test_empty_search(self):
        self.assertEqual(search('xyzxyzxyz'),[])

if __name__=='__main__':
    unittest.main()
