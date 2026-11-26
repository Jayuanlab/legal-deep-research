"""Publish only the validated staging database and retain a recoverable live backup."""
import json,sqlite3,socket,os
import corpus,vectors
from official_bulk import dump

live=corpus.DB;stage=corpus.DATA/'legal-gap185.sqlite3';backup=corpus.DATA/'legal-before-gap185-20261113.sqlite3'
assert all(p.resolve().parent==corpus.DATA.resolve() for p in (live,stage,backup))
assert live.exists() and stage.exists() and not backup.exists()
with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8765))!=0,'Stop server before switch'
v=json.loads((corpus.DATA/'gap185-validation.json').read_text(encoding='utf-8'))
assert v['failures']==v['errors']==v['source_audit_problems']==0
smoke=json.loads((corpus.DATA.parent/'evaluation/gap185-smoke.json').read_text(encoding='utf-8'))
assert smoke['queries']==13 and not any('error' in r for r in smoke['details'])
corpus.DB=stage;assert vectors.status()['ready']
assert corpus.stats()==json.loads((corpus.DATA/'gap185-import-manifest.json').read_text(encoding='utf-8'))['after']
current=sqlite3.connect(live);target=sqlite3.connect(stage)
try:
 assert not current.execute("SELECT count(*) FROM research_jobs WHERE status IN ('running','queued')").fetchone()[0]
 jobs=current.execute('SELECT id,status,payload,updated_at,cancel_requested FROM research_jobs').fetchall()
 with target:
  target.execute('DELETE FROM research_jobs');target.executemany('INSERT INTO research_jobs VALUES(?,?,?,?,?)',jobs)
finally:current.close();target.close()
os.replace(live,backup)
try:os.replace(stage,live)
except Exception:os.replace(backup,live);raise
corpus.DB=live
result=dict(counts=corpus.stats(),vectors=vectors.status(),preserved_jobs=len(jobs),backup=backup.name)
dump(corpus.DATA/'gap185-publication.json',result);print(json.dumps(result))
