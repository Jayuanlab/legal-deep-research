"""Stage a bulk corpus using the live DB's cached vectors, without interrupting service."""
import json,sqlite3,shutil,os
from pathlib import Path
import corpus
from official_bulk import dump

ROOT=Path(__file__).parent
STAGED=corpus.DATA/'legal-bulk.sqlite3'
if __name__=='__main__':
    if not STAGED.exists():
        with corpus.connection() as db:
            docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
            assert len(docs)==3101,'Unexpected starting corpus'
            archive=ROOT/'evaluation/archives/before-bulk-20261112';archive.mkdir(exist_ok=False)
            dump(archive/'corpus.json',docs)
            for name in ('manifest.json','laws.jsonl','cases.jsonl','controls.jsonl','expansion-smoke.json'):
                shutil.copy2(ROOT/'evaluation'/name,archive/name)
            with sqlite3.connect(STAGED) as target:db.backup(target)
            target.close()
    corpus.DB=STAGED
    print(json.dumps(corpus.rebuild()),flush=True)
    os.environ['LEGAL_INDEX_WORKERS']='16';os.environ['LEGAL_INDEX_BATCH_SIZE']='10'
    import vectors
    result=vectors.build()
    dump(corpus.DATA/'bulk-index-status.json',result)
    print(json.dumps(result),flush=True)
