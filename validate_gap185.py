import json,unittest
from collections import Counter
import corpus
from official_bulk import ROOT,dump
from evaluation.build_dataset import corpus_fingerprint
from evaluation.evaluate import load_dataset

corpus.DB=corpus.DATA/'legal-gap185.sqlite3'
with corpus.connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
old=json.loads((ROOT/'evaluation/archives/before-gap185-20261113/corpus.json').read_text(encoding='utf-8'))
assert len(old)==44734 and all(docs[k]==v for k,v in old.items())
m=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))
m.update(corpus_sha256=corpus_fingerprint(docs),corpus_counts=dict(Counter(d['doc_type'] for d in docs.values())),corpus_revision='gap185-20261113',corpus_revision_note='沿用400题原问法、qrel和分组，逐条校验原文未变；尚未重跑400题，历史成绩不能作为本轮成绩。')
dump(ROOT/'evaluation/manifest.json',m);load_dataset()
from audit_corpus import audit
a=audit();assert not a['problems']
suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_*.py')
r=unittest.TextTestRunner(verbosity=1).run(suite)
result=dict(tests=r.testsRun,failures=len(r.failures),errors=len(r.errors),source_audit_problems=len(a['problems']),old_documents_preserved=len(old),corpus=corpus.stats())
dump(corpus.DATA/'gap185-validation.json',result)
if not r.wasSuccessful():raise SystemExit(1)
