import corpus
with corpus.connection() as db:
 active=db.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0]
 print('Active jobs:',active)
 if active:raise SystemExit(1)
