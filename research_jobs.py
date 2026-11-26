import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from corpus import connection
from research_engine import ResearchCancelled
from case_research import research_case as research
from models import ModelError,ModelServiceError

EXECUTOR=ThreadPoolExecutor(max_workers=2,thread_name_prefix='legal-research')
LOCK=threading.Lock()


def now(): return datetime.now(timezone.utc).isoformat()


def setup():
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS research_jobs(id TEXT PRIMARY KEY, status TEXT, payload TEXT, updated_at TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0)')
        # A process restart must not pretend that its interrupted workers still run.
        db.execute("UPDATE research_jobs SET status='interrupted',updated_at=? WHERE status IN ('queued','running')",(now(),))


def get_job(key):
    with connection() as db:
        row=db.execute('SELECT status,payload,updated_at,cancel_requested FROM research_jobs WHERE id=?',(key,)).fetchone()
    if not row:return None
    return dict(json.loads(row[1]),id=key,status=row[0],updated_at=row[2],cancel_requested=bool(row[3]))


def cancelled(key):
    with connection() as db:
        row=db.execute('SELECT cancel_requested FROM research_jobs WHERE id=?',(key,)).fetchone()
    return not row or bool(row[0])


def save(key,payload,state):
    with connection() as db:
        if state=='completed':
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT cancel_requested FROM research_jobs WHERE id=?',(key,)).fetchone()
            if row and row[0]:
                state='cancelled';payload.pop('result',None);payload['error']='研究已取消，未完成结果不作为报告。'
        db.execute('UPDATE research_jobs SET status=?,payload=?,updated_at=? WHERE id=?',(state,json.dumps(payload,ensure_ascii=False),now(),key))


def run(key,question,case_context=None,client_goal=None):
    payload=dict(question=question,events=[])
    if case_context is not None:payload['case_snapshot']=case_context
    if client_goal is not None:payload['client_goal']=client_goal
    def emit(row):
        row=dict(row)
        checkpoint=row.pop('checkpoint',None)
        if checkpoint is not None:payload['checkpoint']=checkpoint
        payload['events'].append(row);save(key,payload,'running')
    try:
        save(key,payload,'running')
        if os.environ.get('LEGAL_RULE_DEMO')=='1':
            from server import research as demo_research
            result=demo_research(question)
            result.update(outcome='limited',stop_reason='离线规则演示，未运行模型拆题或支持性验证。',budget={},supplement_rounds=0)
            for row in result['events']:emit(row)
        else:
            kwargs=dict(emit=emit,cancelled=lambda:cancelled(key))
            if case_context is not None:kwargs['case_context']=case_context
            if client_goal is not None:kwargs['client_goal']=client_goal
            result=research(question,**kwargs)
        if cancelled(key): raise ResearchCancelled()
        payload['result']=result;save(key,payload,'completed')
    except ResearchCancelled:
        payload['error']='研究已取消，未完成结果不作为报告。';save(key,payload,'cancelled')
    except ModelError as error:
        if hasattr(error,'draft_diagnostic'):payload['draft_diagnostic']=error.draft_diagnostic
        if hasattr(error,'ledger_diagnostics'):payload['ledger_diagnostics']=error.ledger_diagnostics
        if isinstance(error,ModelServiceError):payload['error_details']=dict(service=error.service,code=error.code,attempts=error.attempts,retryable=error.retryable,status=error.status)
        payload['error']=str(error);save(key,payload,'failed')
    except Exception:
        payload['error']='研究执行异常，已保留步骤记录。';save(key,payload,'failed')


def start_job(question,case_context=None,client_goal=None):
    with LOCK:
        with connection() as db:
            active=db.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0]
            if active>=2: raise ModelError('已有两项研究正在运行，请稍后再试。')
            key=uuid.uuid4().hex
            db.execute('INSERT INTO research_jobs(id,status,payload,updated_at) VALUES(?,?,?,?)',
                (key,'queued',json.dumps(dict(question=question,events=[]),ensure_ascii=False),now()))
        EXECUTOR.submit(run,key,question,case_context,client_goal)
    return get_job(key)


def cancel_job(key):
    with connection() as db:
        db.execute("UPDATE research_jobs SET cancel_requested=1 WHERE id=? AND status IN ('queued','running')",(key,))
    return get_job(key)
