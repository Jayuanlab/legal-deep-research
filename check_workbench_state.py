from corpus import connection
with connection() as db:
 active=db.execute("SELECT id,status FROM research_jobs WHERE status IN ('running','queued')").fetchall()
print('Active jobs:',active)
if active:raise SystemExit(1)
