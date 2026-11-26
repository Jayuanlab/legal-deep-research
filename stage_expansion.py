"""Build an isolated index; keep the running corpus usable until publication."""
import json,sqlite3,shutil
from pathlib import Path
import corpus
from collect_laws_extra import write_json

ROOT=Path(__file__).parent
STAGED=corpus.DATA/'legal-next.sqlite3'
SNAPSHOT=ROOT/'evaluation/archives/corpus-before-expansion-20261112.json'

def stage():
    if STAGED.exists():raise ValueError('Staged database already exists; inspect before reuse')
    with corpus.connection() as db:
        if db.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0]:raise ValueError('Research jobs are active')
        docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
        assert len(docs)==2592
        if SNAPSHOT.exists():raise ValueError('Historical snapshot already exists')
        write_json(SNAPSHOT,docs)
        archive=ROOT/'evaluation/archives/retrieval-v2-before-corpus-expansion'
        archive.mkdir()
        for name in ('manifest.json','laws.jsonl','cases.jsonl','controls.jsonl','quality-audit.json'):
            shutil.copy2(ROOT/'evaluation'/name,archive/name)
        for name in ('results','results-aliyun'):
            shutil.copytree(ROOT/'evaluation'/name,archive/name)
        shutil.copy2(ROOT/'evaluation/evaluate.py',archive/'evaluate-original.py')
        with sqlite3.connect(STAGED) as target:db.backup(target)
    corpus.DB=STAGED
    print(json.dumps(corpus.rebuild()),flush=True)
    import vectors
    print(json.dumps(vectors.build()),flush=True)
    import audit_corpus
    result=audit_corpus.audit()
    if result['problems']:raise ValueError(result['problems'])
    print('STAGED_INDEX_VERIFIED',flush=True)

if __name__=='__main__':stage()
