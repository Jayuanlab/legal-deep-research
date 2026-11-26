"""Atomically switch a fully validated local index, preserving latest job records."""
import json,os,socket,sqlite3
from pathlib import Path
import corpus
from vectors import status

ROOT=Path(__file__).parent
if __name__=='__main__':
    live=corpus.DB;staged=corpus.DATA/'legal-bulk.sqlite3';backup=corpus.DATA/'legal-before-bulk.sqlite3'
    assert all(p.resolve().parent==corpus.DATA.resolve() for p in (live,staged,backup))
    if not live.exists() or not staged.exists() or backup.exists():raise ValueError('Unexpected publication state; no file overwritten')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',8765))==0:raise ValueError('Stop the HTTP service before publication')
    corpus.DB=staged
    expected=json.loads((corpus.DATA/'bulk-import-manifest.json').read_text(encoding='utf-8'))['after']
    assert corpus.stats()==expected and status()['ready']
    validation=json.loads((corpus.DATA/'bulk-validation.json').read_text(encoding='utf-8'))
    assert validation['failures']==validation['errors']==validation['source_audit_problems']==0
    current=sqlite3.connect(live);target=sqlite3.connect(staged)
    try:
        if current.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0]:raise ValueError('Active research task; publication aborted')
        jobs=current.execute('SELECT id,status,payload,updated_at,cancel_requested FROM research_jobs').fetchall()
        with target:
            target.execute('DELETE FROM research_jobs');target.executemany('INSERT INTO research_jobs VALUES(?,?,?,?,?)',jobs)
    finally:current.close();target.close()
    os.replace(live,backup)
    try:os.replace(staged,live)
    except Exception:
        os.replace(backup,live);raise
    corpus.DB=live
    print(json.dumps(dict(counts=corpus.stats(),vectors=status(),preserved_jobs=len(jobs),backup=backup.name)),flush=True)
