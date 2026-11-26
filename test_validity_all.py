import json,unittest,hashlib
from pathlib import Path
import corpus
from law_validity import load_rules,enrich
from validity_evidence import titles,canonical,repeal_targets
class AllValidityTests(unittest.TestCase):
 def test_every_source_version_has_a_ledger_row(self):
  rows=json.loads((corpus.DATA/'validity-all-ledger.json').read_text(encoding='utf-8'))
  self.assertEqual(len(rows),1204);self.assertEqual(sum(r['records'] for r in rows),52995)
  self.assertTrue(all(r['outcome'] and r['checked_at']=='2026-11-13' for r in rows))
 def test_nested_quoted_law_is_not_the_repealed_implementation_rules(self):
  ts=repeal_targets('《中华人民共和国海关法行政处罚实施细则》同时废止')
  self.assertEqual(len(ts),1)
  self.assertNotEqual(canonical(ts[0]['name']),canonical('中华人民共和国海关法'))
  rows=corpus.library('中华人民共和国海关法','law')['items']
  self.assertTrue(all(d['validity']['code']!='repealed' for d in rows))
 def test_2020_consolidated_edition_is_not_old_merely_due_to_2021_effective_date(self):
  with corpus.connection() as db:d=json.loads(db.execute('SELECT payload FROM documents WHERE id=?',('E31001',)).fetchone()[0])
  self.assertNotIn(d['validity']['code'],('superseded','partially_repealed','repealed'))
 def test_rules_are_bound_to_source_version_and_text(self):
  rules=load_rules();k=next(k for k,v in rules.items() if v['code']=='superseded')
  with corpus.connection() as db:d=json.loads(db.execute('SELECT payload FROM documents WHERE id=?',(k,)).fetchone()[0])
  changed=dict(d,source_sha256='changed',reference_status='unknown')
  self.assertEqual(enrich(changed,rules)['validity']['code'],'unknown')
  self.assertNotEqual(enrich(changed,rules)['reference_status'],'not_reference')
 def test_old_versions_remain_browsable_and_all_excluded(self):
  rows=corpus.library(validity='superseded',size=3000)
  self.assertEqual(rows['total'],1960)
  self.assertTrue(all(d['reference_status']=='not_reference' and d['validity'].get('evidence_quote') for d in rows['items']))
 def test_source_evidence_bytes_are_verified_once_per_archive(self):
  rules=load_rules();seen=set()
  for r in rules.values():
   if r.get('raw_path') and r.get('source_sha256'):
    key=(r['raw_path'],r['source_sha256'])
    if key in seen:continue
    seen.add(key);self.assertEqual(hashlib.sha256((corpus.DATA/key[0]).read_bytes()).hexdigest(),key[1])
if __name__=='__main__':unittest.main()
