import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from corpus import connection,search,outside_scope,terms
from models import embed,embedding_identity,ModelError


def content_hash(doc):
    return hashlib.sha256((doc['title']+'\n'+doc['text']).encode('utf-8')).hexdigest()


def chunks(doc,size=1800,overlap=120):
    text=doc['text'];parts=[];start=0
    while start<len(text):
        end=min(start+size,len(text))
        if end<len(text):
            newline=text.rfind('\n',start+size//2,end)
            if newline>start:end=newline
        parts.append(dict(index=len(parts),start=start,end=end,text=text[start:end]))
        if end==len(text):break
        start=max(start+1,end-overlap)
    for part in parts:
        part['id']=doc['id'] if len(parts)==1 else doc['id']+'_'+str(part['index'])
        part['hash']=content_hash(dict(title=doc['title'],text=part['text']))
    return parts


def setup():
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS vectors(id TEXT, identity TEXT, content_hash TEXT, vector TEXT, PRIMARY KEY(id,identity))')
        db.execute('CREATE TABLE IF NOT EXISTS vector_chunks(doc_id TEXT, chunk_index INTEGER, identity TEXT, content_hash TEXT, chunk_hash TEXT, start INTEGER, end INTEGER, vector TEXT, PRIMARY KEY(doc_id,chunk_index,identity))')


def load(include_vectors=True):
    setup();identity=embedding_identity()
    with connection() as db:
        docs={key:json.loads(value) for key,value in db.execute('SELECT id,payload FROM documents')}
        column='vector' if include_vectors else 'NULL'
        cached={(row[0],row[1]):row for row in db.execute('SELECT doc_id,chunk_index,content_hash,chunk_hash,start,end,'+column+' FROM vector_chunks WHERE identity=?',(identity,))}
    return identity,docs,cached


def valid_cached(doc,part,row):
    return row is not None and row[2]==content_hash(doc) and row[3]==part['hash'] and row[4:6]==(part['start'],part['end'])


def build():
    workers=int(os.environ.get('LEGAL_INDEX_WORKERS','1'))
    batch_size=int(os.environ.get('LEGAL_INDEX_BATCH_SIZE','8'))
    if not 1<=workers<=16 or not 1<=batch_size<=10:raise ValueError('Index workers must be 1..16, batch size 1..10')
    identity,docs,cached=load(False);pending=[];migrated=[]
    with connection() as db:
        legacy={key:(digest,value) for key,digest,value in db.execute('SELECT id,content_hash,vector FROM vectors WHERE identity=?',(identity,))}
    for doc in docs.values():
        parts=chunks(doc)
        for part in parts:
            if valid_cached(doc,part,cached.get((doc['id'],part['index']))):continue
            if len(parts)==1 and doc['id'] in legacy and legacy[doc['id']][0]==content_hash(doc):
                migrated.append((doc,part,legacy[doc['id']][1]))
            else:pending.append((doc,part))
    def store(rows):
        with connection() as db:
            db.executemany('INSERT OR REPLACE INTO vector_chunks VALUES(?,?,?,?,?,?,?,?)',[
                (d['id'],p['index'],identity,content_hash(d),p['hash'],p['start'],p['end'],v) for d,p,v in rows])
    store(migrated)
    print(f'Reused {len(migrated)} legacy vectors; {len(pending)} chunks need embedding',flush=True)
    batches=[pending[i:i+batch_size] for i in range(0,len(pending),batch_size)]
    def process(batch):
        values=embed([d['title']+'\n'+p['text'] for d,p in batch])
        return [(d,p,json.dumps(v)) for (d,p),v in zip(batch,values)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for n,rows in enumerate(pool.map(process,batches),1):
            store(rows);print(f'Indexed batch {n}/{len(batches)}: {rows[-1][1]["id"]}',flush=True)
    return status()


def status():
    _,docs,cached=load(False);ready=0;total_chunks=0;indexed_chunks=0
    for doc in docs.values():
        parts=chunks(doc);total_chunks+=len(parts)
        count=sum(valid_cached(doc,p,cached.get((doc['id'],p['index']))) for p in parts)
        indexed_chunks+=count;ready+=count==len(parts)
    return dict(indexed=ready,total=len(docs),chunks=total_chunks,indexed_chunks=indexed_chunks,ready=ready==len(docs))


def retrieve(question,timeout=120):
    if outside_scope(question):return []
    _,docs,cached=load();usable=[]
    for doc in docs.values():
        for part in chunks(doc):
            row=cached.get((doc['id'],part['index']))
            if not valid_cached(doc,part,row):raise ModelError('向量索引缺失或已过期，请先运行 vectors.py。')
            if doc.get('reference_status')!='not_reference':usable.append((doc,part,row[6]))
    q=embed([question],query=True,timeout=timeout)[0]
    best={}
    for doc,part,raw in usable:
        vector=json.loads(raw)
        if len(vector)!=len(q):raise ModelError('缓存向量维度不匹配，请重建索引。')
        score=sum(a*b for a,b in zip(q,vector))
        if doc['id'] not in best or score>best[doc['id']][0]:best[doc['id']]=(score,part)
    ranked=sorted(best,key=lambda key:best[key][0],reverse=True);output=[]
    for kind,limit in [('law',4),('case',2)]:
        semantic=[key for key in ranked if docs[key]['doc_type']==kind][:20]
        lexical=search(question,limit=20,doc_type=kind);scores={}
        for ids in (semantic,[d['id'] for d in lexical]):
            for rank,key in enumerate(ids,1):
                if key in best:scores[key]=scores.get(key,0)+1/(60+rank)
        for key in sorted(scores,key=scores.get,reverse=True)[:limit]:
            similarity,part=best[key]
            output.append(dict(docs[key],id=part['id'],parent_id=key,text=part['text'],
                fragment=dict(index=part['index'],start=part['start'],end=part['end'],source_length=len(docs[key]['text'])),
                score=round(scores[key],6),vector_similarity=round(similarity,5),retrieval='全文分片向量 + BM25 / RRF'))
    return output


def retrieve_lexical(question):
    """Explicit degraded retrieval; keep exact bounded spans and source IDs."""
    tokens=set(terms(question).split());output=[]
    for kind,limit in [('law',4),('case',2)]:
        for doc in search(question,limit=limit,doc_type=kind):
            part=max(chunks(doc),key=lambda p:len(tokens&set(terms(p['text']).split())))
            output.append(dict(doc,id=part['id'],parent_id=doc['id'],text=part['text'],
                fragment=dict(index=part['index'],start=part['start'],end=part['end'],source_length=len(doc['text'])),
                retrieval='本地 BM25（向量服务不可用，未使用语义向量）'))
    return output


if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False))
