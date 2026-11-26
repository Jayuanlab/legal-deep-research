"""Synchronize final metadata, retain old qrels, and validate staged sources offline."""
import json,unittest
from pathlib import Path
from collections import Counter
import corpus
from official_bulk import dump

ROOT=Path(__file__).parent
if __name__=='__main__':
    corpus.DB=corpus.DATA/'legal-bulk.sqlite3'
    print(json.dumps(corpus.rebuild()),flush=True)
    with corpus.connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
    old=json.loads((ROOT/'evaluation/archives/before-bulk-20261112/corpus.json').read_text(encoding='utf-8'))
    assert len(old)==3101 and all(docs[k]==v for k,v in old.items()),'Existing corpus text or metadata changed'
    expected=json.loads((corpus.DATA/'bulk-import-manifest.json').read_text(encoding='utf-8'))['after']
    assert corpus.stats()==expected
    # Only the newly recovered guide is absent from the ongoing bulk worker's
    # source snapshot. Add that guide without repeating the remaining batch API calls.
    from vectors import chunks,content_hash
    from models import embed,embedding_identity
    doc=docs['C1045'];identity=embedding_identity();parts=chunks(doc)
    with corpus.connection() as db:
        rows={n:h for n,h in db.execute('SELECT chunk_index,chunk_hash FROM vector_chunks WHERE identity=? AND doc_id=?',(identity,doc['id']))}
    missing=[p for p in parts if rows.get(p['index'])!=p['hash']]
    if missing:
        values=embed([doc['title']+'\n'+p['text'] for p in missing])
        with corpus.connection() as db:
            db.executemany('INSERT OR REPLACE INTO vector_chunks VALUES(?,?,?,?,?,?,?,?)',[(doc['id'],p['index'],identity,content_hash(doc),p['hash'],p['start'],p['end'],json.dumps(v)) for p,v in zip(missing,values)])
    from evaluation.build_dataset import corpus_fingerprint
    manifest=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))
    manifest.update(corpus_sha256=corpus_fingerprint(docs),corpus_counts=dict(Counter(d['doc_type'] for d in docs.values())),corpus_revision='national-bulk-20261112',corpus_revision_note='沿用400题原问法、qrel与分组，逐条核对标注原文未变；扩大的候选库需要独立输出重评，旧结果不可作为本轮成绩。')
    dump(ROOT/'evaluation/manifest.json',manifest)
    from evaluation.evaluate import load_dataset
    load_dataset()
    import audit_corpus
    audit=audit_corpus.audit();assert not audit['problems'],audit['problems']
    suite=unittest.defaultTestLoader.discover(str(ROOT),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    dump(corpus.DATA/'bulk-validation.json',dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),source_audit_problems=len(audit['problems']),preserved_original_documents=len(old)))
    if not result.wasSuccessful():raise SystemExit(1)
