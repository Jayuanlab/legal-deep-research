"""Run only after the bulk embedding worker exits; reconcile final titles and validate."""
import os,runpy,json
from pathlib import Path
import corpus
from official_bulk import dump

ROOT=Path(__file__).parent
if __name__=='__main__':
    runpy.run_path(str(ROOT/'merge_official_bulk.py'),run_name='__main__')
    corpus.DB=corpus.DATA/'legal-bulk.sqlite3'
    print(json.dumps(corpus.rebuild()),flush=True)
    os.environ['LEGAL_INDEX_WORKERS']='8';os.environ['LEGAL_INDEX_BATCH_SIZE']='10'
    import vectors
    result=vectors.build();assert result['ready']
    dump(corpus.DATA/'bulk-index-status.json',result)
    # Full validation repeats only because final source labels/titles changed.
    runpy.run_path(str(ROOT/'validate_bulk_stage.py'),run_name='__main__')
