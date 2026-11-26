import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA = Path(__file__).parent / 'data'
DB = DATA / 'legal.sqlite3'


@contextmanager
def connection():
    db=sqlite3.connect(DB,timeout=30)
    try:
        with db:
            yield db
    finally:
        db.close()


def terms(text):
    # Preserve word boundaries instead of creating bigrams across punctuation.
    words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text.lower())
    return ' '.join(t for word in words for t in ([word] if not re.match(r'[\u4e00-\u9fff]', word) or len(word)==1 else [word[i:i+2] for i in range(len(word)-1)]))


def rebuild():
    DATA.mkdir(exist_ok=True)
    docs=[]
    for name in ('laws.json','laws-extra.json','laws-expansion.json','laws-regulations.json','laws-national.json','laws-judicial-bulk.json','laws-gap185.json','cases.json','cases-extra.json','cases-guiding-extra.json','cases-bulk.json'):
        path=DATA/name
        if path.exists():
            docs.extend(json.loads(path.read_text(encoding='utf-8')))
    if not docs:
        raise ValueError('请先运行 ingest.py 建库。')
    from law_validity import enrich,load_rules
    rules=load_rules();docs=[enrich(doc,rules) for doc in docs]
    ids=set()
    for doc in docs:
        if doc['id'] in ids or not doc['text'] or '\ufffd' in doc['text'] or '???' in doc['title']:
            raise ValueError('重复编号或损坏文本：'+doc['id'])
        ids.add(doc['id'])
    with connection() as db:
        db.executescript('CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, doc_type TEXT NOT NULL, payload TEXT NOT NULL); CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(id UNINDEXED, body);')
        db.execute('DELETE FROM documents'); db.execute('DELETE FROM search_index')
        for doc in docs:
            db.execute('INSERT INTO documents VALUES(?,?,?)',(doc['id'],doc['doc_type'],json.dumps(doc,ensure_ascii=False)))
            tags=doc.get('tags','')
            if isinstance(tags,list): tags=' '.join(tags)
            db.execute('INSERT INTO search_index VALUES(?,?)',(doc['id'],terms(doc['title']+' '+doc['text']+' '+tags)))
        stored=[json.loads(r[0]) for r in db.execute('SELECT payload FROM documents')]
        assert len(stored)==len(docs) and all(d['title']==s['title'] for d,s in zip(docs,stored))
    return stats()


def stats():
    with connection() as db:
        counts=dict(db.execute('SELECT doc_type,count(*) FROM documents GROUP BY doc_type'))
    return dict(laws=counts.get('law',0),cases=counts.get('case',0),total=sum(counts.values()))


def outside_scope(query):
    # Missing subject-matter sources are handled by the evidence assessment,
    # rather than a stale keyword block list as the collection expands.
    return False


def search(query,limit=5,doc_type=None):
    if outside_scope(query):
        return []
    tokens=sorted(set(terms(query).split()))[:300]
    if not tokens:
        return []
    sql="SELECT d.payload,bm25(search_index) FROM search_index JOIN documents d ON d.id=search_index.id WHERE search_index MATCH ? AND coalesce(json_extract(d.payload,'$.reference_status'),'unknown')!='not_reference'"
    args=[' OR '.join('"'+t+'"' for t in tokens)]
    if doc_type:
        sql+=' AND d.doc_type=?'; args.append(doc_type)
    sql+=' ORDER BY bm25(search_index), d.id LIMIT ?'; args.append(limit)
    with connection() as db:
        return [dict(json.loads(payload),score=round(-score,6)) for payload,score in db.execute(sql,args)]


def library(query='',doc_type='law',page=1,size=20,topic=None,validity=None):
    from law_validity import LABELS
    if validity and (doc_type!='law' or validity not in LABELS):raise ValueError('无效效力状态')
    with connection() as db:
        if query:
            tokens=sorted(set(terms(query).split()))[:100]
            if not tokens:
                return dict(items=[],total=0,page=page)
            clause=' FROM documents d JOIN search_index s ON d.id=s.id WHERE d.doc_type=? AND search_index MATCH ?'
            args=[doc_type,' AND '.join('"'+t+'"' for t in tokens)]
        else:
            clause=' FROM documents d WHERE d.doc_type=?'; args=[doc_type]
        if topic:
            clause+=" AND json_extract(d.payload,'$.topic')=?"; args.append(topic)
        if validity:
            clause+=" AND coalesce(json_extract(d.payload,'$.validity.code'),'unknown')=?";args.append(validity)
        total=db.execute('SELECT count(*)'+clause,args).fetchone()[0]
        # A complete law name should rank its own articles ahead of older
        # documents that merely cite that law and share all query bigrams.
        order=" ORDER BY (json_extract(d.payload,'$.law_name')=?) DESC,d.rowid" if query and doc_type=='law' else ' ORDER BY d.rowid'
        order_args=[query.strip()] if query and doc_type=='law' else []
        rows=db.execute('SELECT d.payload'+clause+order+' LIMIT ? OFFSET ?',args+order_args+[size,(page-1)*size]).fetchall()
    return dict(items=[json.loads(r[0]) for r in rows],total=total,page=page)


def catalog():
    with connection() as db:
        laws=db.execute("SELECT json_extract(payload,'$.law_name'),json_extract(payload,'$.version'),count(*) FROM documents WHERE doc_type='law' GROUP BY 1,2").fetchall()
        topics=db.execute("SELECT json_extract(payload,'$.topic'),count(*) FROM documents WHERE doc_type='law' GROUP BY 1").fetchall()
        case_topics=db.execute("SELECT json_extract(payload,'$.topic'),count(*) FROM documents WHERE doc_type='case' GROUP BY 1").fetchall()
    coverage=None
    coverage_path=DATA/'national-coverage.json'
    bulk_path=DATA/('gap185-import-manifest.json' if (DATA/'gap185-import-manifest.json').exists() else 'bulk-import-manifest.json')
    if coverage_path.exists() and bulk_path.exists() and json.loads(bulk_path.read_text(encoding='utf-8'))['after']==stats():
        c=json.loads(coverage_path.read_text(encoding='utf-8'))
        coverage=dict(benchmark=c['benchmark'],title_matches=c['title_matches'],benchmark_titles=c['parsed_names'],missing_titles=len(c['missing_names']),all_china_complete=False,
            note=(f"目录仍有{len(c['missing_names'])}个标题缺少原文。" if c['missing_names'] else '303件基准目录标题均已存档；其中来源状态存疑的记录默认不参与研究。')+'同名规范仍须核对版本和时间效力；地方性法规、部门及地方政府规章尚未系统收录。')
    return dict(laws=[dict(name=n,version=v,count=c) for n,v,c in laws],topics=[dict(name=n,count=c) for n,c in topics if n],coverage=coverage,
        case_topics=[dict(name=n,count=c) for n,c in case_topics if n],
        case_scope='官方指导案例及典型案例发布文本；两类效力不同，已核对停止参照或废止的记录默认不参与研究，其余仍须核验个案适用',network_search=False)


if __name__=='__main__':
    print(json.dumps(rebuild(),ensure_ascii=False))
