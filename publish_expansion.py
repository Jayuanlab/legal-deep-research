"""Publish a verified staged database after stopping the HTTP service."""
import json,os,socket,sqlite3
import corpus
from vectors import status

if __name__=='__main__':
    live=corpus.DB;staged=corpus.DATA/'legal-next.sqlite3';backup=corpus.DATA/'legal-before-expansion.sqlite3'
    root=corpus.DATA.resolve()
    assert all(p.resolve().parent==root for p in (live,staged,backup))
    if not live.exists() or not staged.exists() or backup.exists():raise ValueError('Unexpected database publication state')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1',8765))==0:raise ValueError('Stop the HTTP service before publication')
    corpus.DB=staged
    assert corpus.stats()==dict(laws=2782,cases=319,total=3101)
    assert status()['ready']
    with sqlite3.connect(live) as current:
        if current.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0]:raise ValueError('Active research jobs; publication aborted')
        jobs=current.execute('SELECT id,status,payload,updated_at,cancel_requested FROM research_jobs').fetchall()
    with sqlite3.connect(staged) as target:
        target.execute('DELETE FROM research_jobs')
        target.executemany('INSERT INTO research_jobs VALUES(?,?,?,?,?)',jobs)
    current.close();target.close()
    os.replace(live,backup)
    try:os.replace(staged,live)
    except Exception:
        os.replace(backup,live);raise
    corpus.DB=live
    print(json.dumps(dict(counts=corpus.stats(),vectors=status(),preserved_research_jobs=len(jobs),backup=backup.name)),flush=True)
