"""Validate the expanded corpus and rebind unchanged eval labels to its snapshot."""
import json,unittest
from collections import Counter
from pathlib import Path
import corpus
from collect_laws_extra import write_json
from evaluation.build_dataset import corpus_fingerprint
from evaluation.evaluate import load_dataset

ROOT=Path(__file__).parent
if __name__=='__main__':
    corpus.DB=corpus.DATA/'legal-next.sqlite3'
    with corpus.connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
    old=json.loads((ROOT/'evaluation/archives/corpus-before-expansion-20261112.json').read_text(encoding='utf-8'))
    assert all(docs[k]==v for k,v in old.items()),'Pre-existing source changed'
    assert len(docs)==3101
    manifest_path=ROOT/'evaluation/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update(corpus_sha256=corpus_fingerprint(docs),corpus_counts=dict(Counter(d['doc_type'] for d in docs.values())),
        corpus_revision='expansion-20261112-468-laws-41-cases',
        corpus_revision_note='400题问法、qrel及分组保持原样；逐条校验引用原文未漂移。扩大候选库后须生成独立结果，旧结果为扩库前基线。')
    write_json(manifest_path,manifest)
    load_dataset()  # Full fingerprint and every qrel anchor checked before tests.
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
