"""Evaluate fixed local retrieval. Query embedding API is opt-in and resumable."""
import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import vectors
from corpus import connection,search
from models import embed,config
from evaluation.build_dataset import digest,normalized,corpus_fingerprint

ROOT=Path(__file__).parent

def load_dataset(dataset_dir=None,corpus_snapshot=None):
    root=Path(dataset_dir).resolve() if dataset_dir else ROOT
    rows=[json.loads(line) for name in ('laws','cases','controls') for line in (root/(name+'.jsonl')).read_text(encoding='utf-8').splitlines() if line.strip()]
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    bare=[{k:v for k,v in r.items() if k!='version'} for r in rows]
    if digest(json.dumps(bare,ensure_ascii=False,sort_keys=True))!=manifest['dataset_sha256']:raise ValueError('Dataset fingerprint changed; rebuild/version the dataset')
    if corpus_snapshot:
        docs=json.loads(Path(corpus_snapshot).read_text(encoding='utf-8'))
    else:
        with connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
    fingerprint=corpus_fingerprint(docs)
    if fingerprint!=manifest['corpus_sha256']:raise ValueError('Corpus changed; re-review qrels and version the dataset')
    if len({r['id'] for r in rows})!=len(rows):raise ValueError('Duplicate query IDs')
    for row in rows:
        if row['version']!=manifest['version']:raise ValueError('Dataset row version mismatch')
        if not row['query'].strip():raise ValueError('Blank query')
        seen=set()
        for q in row['qrels']:
            doc=docs[q['doc_id']]
            if q['doc_id'] in seen or q['grade'] not in (1,2):raise ValueError('Invalid qrels')
            seen.add(q['doc_id'])
            if doc['doc_type']!=row['collection'] or digest(doc['text'])!=q['text_sha256'] or normalized(q['evidence_quote']) not in normalized(doc['text']):raise ValueError('Qrel evidence drift')
            if doc.get('reference_status')=='not_reference':raise ValueError('Withdrawn case cannot be a positive')
    dev={q['doc_id'] for r in rows if r['split']=='dev' for q in r['qrels']}
    test={q['doc_id'] for r in rows if r['split']=='test' for q in r['qrels']}
    if dev&test:raise ValueError('Source leakage across splits')
    return rows,manifest,docs

def canonical(doc):return doc.get('parent_id') or doc['id'].split('_')[0]

def score(ranked,qrels,k,passage=False):
    unique=[];seen=set()
    for doc in ranked:
        key=canonical(doc)
        if key not in seen:unique.append(doc);seen.add(key)
    top=unique[:k];ids=[canonical(d) for d in top];grades={q['doc_id']:q['grade'] for q in qrels if q['grade']>0}
    if not grades:return None
    hits=set(ids)&set(grades)
    dcg=sum((2**grades.get(key,0)-1)/math.log2(i+2) for i,key in enumerate(ids))
    ideal=sum((2**g-1)/math.log2(i+2) for i,g in enumerate(sorted(grades.values(),reverse=True)[:k]))
    anchors=sum(any(canonical(d)==q['doc_id'] and normalized(q['evidence_quote']) in normalized(d['text']) for d in top) for q in qrels)
    return dict(hit_at_1=float(bool(ids and ids[0] in grades)),hit_at_k=float(bool(hits)),known_recall_at_k=len(hits)/len(grades),
                mrr_at_k=next((1/(i+1) for i,key in enumerate(ids) if key in grades),0),known_ndcg_at_k=dcg/ideal if ideal else 0,
                anchor_recall_at_k=anchors/len(grades) if passage else None)

def query_vectors(rows,identity,dimension,allow_network):
    path=ROOT/('query_vectors-'+identity[:12]+'.json')
    cache=json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(identity=identity,task='query',model=config()[1]['model'],dimensions=dimension,entries={})
    if cache['identity']!=identity:raise ValueError('Embedding identity mismatch')
    entries=cache['entries'];missing=[r['query'] for r in rows if digest(r['query']) not in entries]
    missing=list(dict.fromkeys(missing))
    if missing and not allow_network:raise ValueError(f'{len(missing)} query vectors missing; use --embed-missing for the existing embedding API')
    for start in range(0,len(missing),8):
        batch=missing[start:start+8];values=embed(batch,query=True)
        for query,value in zip(batch,values):entries[digest(query)]=dict(query=query,vector=value)
        cache['updated_at']=datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(cache,ensure_ascii=False),encoding='utf-8')
        print(f'Embedded queries {min(start+8,len(missing))}/{len(missing)}',flush=True)
    result={}
    for row in rows:
        entry=entries[digest(row['query'])];v=entry['vector']
        if entry['query']!=row['query'] or len(v)!=dimension or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in v) or abs(sum(x*x for x in v)-1)>1e-4:raise ValueError('Invalid cached query vector')
        result[row['query']]=v
    return result,path

def semantic_rank(query_vector,usable,kind,k):
    best={}
    for doc,part,v in usable:
        if doc['doc_type']!=kind:continue
        cosine=sum(a*b for a,b in zip(query_vector,v))
        if doc['id'] not in best or cosine>best[doc['id']][0]:best[doc['id']]=(cosine,part)
    keys=sorted(best,key=lambda key:best[key][0],reverse=True)[:k]
    return [dict(doc,id=best[doc['id']][1]['id'],parent_id=doc['id'],text=best[doc['id']][1]['text']) for key in keys for doc in [next(d for d,p,v in usable if d['id']==key)]]

def run(args):
    rows,manifest,docs=load_dataset(getattr(args,'dataset',None))
    if args.split!='all':rows=[r for r in rows if r['split']==args.split]
    if getattr(args,'query_ids',None):
        selected=set(args.query_ids.split(','))
        if selected-{r['id'] for r in rows}:raise ValueError('Unknown query ID in selected split')
        rows=[r for r in rows if r['id'] in selected]
    identity,vector_docs,cached=vectors.load()
    default_out=ROOT/'results' if not getattr(args,'dataset',None) else ROOT/'results'/manifest['version']
    out=Path(args.output) if getattr(args,'output',None) else default_out
    previous=out/'summary.json'
    if previous.exists():
        baseline=json.loads(previous.read_text(encoding='utf-8'))
        if baseline['embedding_identity']!=identity or baseline['dataset']['corpus_sha256']!=manifest['corpus_sha256'] or baseline['dataset']['dataset_sha256']!=manifest['dataset_sha256']:
            raise ValueError('Existing baseline uses a different model, corpus or dataset; choose a new --output directory')
    usable=[];decoded_vectors={}
    for doc in vector_docs.values():
        for part in vectors.chunks(doc):
            row=cached.get((doc['id'],part['index']))
            if not vectors.valid_cached(doc,part,row):raise ValueError('Stale or missing document vector')
            if doc.get('reference_status')!='not_reference':
                value=json.loads(row[6]);decoded_vectors[row[6]]=value
                usable.append((doc,part,value))
    dimension=len(usable[0][2]);qv={};cache_path=None
    if not args.bm25_only:qv,cache_path=query_vectors(rows,identity,dimension,args.embed_missing)
    methods=['bm25'] if args.bm25_only else ['bm25','vector','hybrid']
    details=[];started=time.perf_counter()
    for n,row in enumerate(rows,1):
        kind=row['collection'];k=4 if kind=='law' else 2
        candidates={'bm25':search(row['query'],limit=k,doc_type=kind)}
        if not args.bm25_only:
            query=row['query'];v=qv[query]
            candidates['vector']=semantic_rank(v,usable,kind,k)
            def cached_embed(texts,query=False,**kwargs):
                if texts!=[row['query']] or not query:raise AssertionError('Unexpected embedding call during cached replay')
                return [v]
            native_loads=json.loads
            def cached_loads(raw,*a,**kw):
                if isinstance(raw,str) and raw in decoded_vectors:return decoded_vectors[raw]
                return native_loads(raw,*a,**kw)
            # Cache transport, snapshot loading and exact JSON decoding only.
            # Ranking, arithmetic, fragment selection, BM25/RRF and quotas stay
            # in production code; JSON document payloads use the native decoder.
            with patch.object(vectors,'embed',side_effect=cached_embed),patch.object(vectors,'load',return_value=(identity,vector_docs,cached)),patch.object(vectors.json,'loads',new=cached_loads):
                candidates['hybrid']=[d for d in vectors.retrieve(query) if d['doc_type']==kind]
        for method in methods:
            ranked=candidates[method];ids=[canonical(d) for d in ranked]
            metrics=score(ranked,row['qrels'],k,passage=method!='bm25')
            forbidden=set(row.get('forbidden_ids',[]))&set(ids)
            details.append(dict(query_id=row['id'],query=row['query'],collection=kind,split=row['split'],domain=row['domain'],style=row['style'],method=method,k=k,
                cohort=row.get('cohort','regression_v1'),source_group=row.get('source_group'),
                metrics=metrics,known_positives=[q['doc_id'] for q in row['qrels']],forbidden_leaks=sorted(forbidden),returned=len(ids),
                control=row['style'] if row['split']=='control' else None,
                candidates=[dict(doc_id=canonical(d),fragment_id=d['id'],title=d['title'],source_url=d['url'],known_grade=next((q['grade'] for q in row['qrels'] if q['doc_id']==canonical(d)),None),
                    anchor_matches=[q['doc_id'] for q in row['qrels'] if q['doc_id']==canonical(d) and normalized(q['evidence_quote']) in normalized(d['text'])]) for d in ranked]))
        print(f'Evaluated {n}/{len(rows)}: {row["id"]}',flush=True)
    groups=[]
    for kind in ('law','case'):
        for split in ('all','dev','test'):
            for method in methods:
                subset=[d for d in details if d['collection']==kind and d['method']==method and d['metrics'] is not None and (split=='all' or d['split']==split)]
                if subset:
                    keys=subset[0]['metrics'];averages={key:statistics.mean(d['metrics'][key] for d in subset if d['metrics'][key] is not None) if any(d['metrics'][key] is not None for d in subset) else None for key in keys}
                    groups.append(dict(collection=kind,split=split,method=method,queries=len(subset),k=subset[0]['k'],**averages))
    controls=[]
    for method in methods:
        control=[d for d in details if d['split']=='control' and d['method']==method]
        withdrawal=[d for d in control if d['control']=='withdrawn'];absent=[d for d in control if d['control']!='withdrawn']
        controls.append(dict(method=method,withdrawn_queries=len(withdrawal),withdrawn_leak_queries=sum(bool(d['forbidden_leaks']) for d in withdrawal),
            no_answer_queries=len(absent),nonempty_no_answer_queries=sum(d['returned']>0 for d in absent)))
    cohorts=[]
    for cohort in sorted({d['cohort'] for d in details}):
        for kind in ('law','case'):
            for method in methods:
                subset=[d for d in details if d['cohort']==cohort and d['collection']==kind and d['method']==method and d['metrics'] is not None]
                if subset:cohorts.append(dict(cohort=cohort,collection=kind,method=method,queries=len(subset),k=subset[0]['k'],**{key:statistics.mean(d['metrics'][key] for d in subset if d['metrics'][key] is not None) if any(d['metrics'][key] is not None for d in subset) else None for key in subset[0]['metrics']}))
    slices=[]
    for field in ('domain','style'):
        for value in sorted({d[field] for d in details if d['metrics'] is not None}):
            subset=[d for d in details if d[field]==value and d['method']=='hybrid' and d['metrics'] is not None]
            if subset:slices.append(dict(field=field,value=value,queries=len(subset),known_recall_at_k=statistics.mean(d['metrics']['known_recall_at_k'] for d in subset),hit_at_k=statistics.mean(d['metrics']['hit_at_k'] for d in subset)))
    summary=dict(created_at=datetime.now(timezone.utc).isoformat(),dataset=manifest,evaluated_rows=len(rows),embedding_identity=identity,embedding_model=config()[1]['model'],dimensions=dimension,query_cache=cache_path.name if cache_path else None,
        cohorts=cohorts,slices=slices,
        rank_replay_seconds=round(time.perf_counter()-started,2),methods=methods,groups=groups,controls=controls,
        note='固定已有检索逻辑；真实查询向量缓存重放，未调用语言模型。法条k=4、案例k=2。指标针对已标注相关来源，不把未标注候选当作已判不相关。耗时排除API向量生成，非线上延迟。')
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'details.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in details),encoding='utf-8')
    pool=[]
    for d in details:
        if d['metrics'] is not None:
            for candidate in d['candidates']:
                if candidate['known_grade'] is None:pool.append(dict(query_id=d['query_id'],query=d['query'],method=d['method'],**candidate,judgment='unjudged'))
    (out/'review_pool.jsonl').write_text(''.join(json.dumps(d,ensure_ascii=False)+'\n' for d in pool),encoding='utf-8')
    write_report(summary,details,out)
    print(json.dumps(dict(version=manifest['version'],rows=len(rows),all_groups=[g for g in groups if g['split']=='all'],controls=controls,rank_replay_seconds=summary['rank_replay_seconds']),ensure_ascii=False))

def write_report(summary,details,out):
    lines=['# 本地法律召回评测基线','',summary['note'],'',
       f"当前报告实际评测{summary.get('evaluated_rows',summary['dataset']['rows'])}题；完整数据版本包含{summary['dataset']['rows']}题。",
       '标注由本次依据官方存档编写并校验引用，尚无独立法律专家复核，不是权威法律问答评测。相关性标注不穷尽全库；未标注候选保留为unjudged，见review_pool.jsonl。','',
       '## 全部正例（描述性汇总）','',
       '| 库 / K | 方法 | 题数 | Hit@1 | Hit@K | 已标注Recall@K | MRR@K | 已标注nDCG@K | 锚点Recall@K |',
       '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for g in summary['groups']:
        if g['split']!='all':continue
        vals=[g[key] for key in ('hit_at_1','hit_at_k','known_recall_at_k','mrr_at_k','known_ndcg_at_k','anchor_recall_at_k')]
        lines.append(f"| {g['collection']} / {g['k']} | {g['method']} | {g['queries']} | "+' | '.join('—' if v is None else f'{v:.3f}' for v in vals)+' |')
    lines+=['','## 固定旧题与新增题分别统计','', '| 题集 | 库 | 方法 | 题数 | Hit@K | 已标注Recall@K | MRR@K |','| --- | --- | --- | ---: | ---: | ---: | ---: |']
    for g in summary.get('cohorts',[]):lines.append(f"| {g['cohort']} | {g['collection']} | {g['method']} | {g['queries']} | {g['hit_at_k']:.3f} | {g['known_recall_at_k']:.3f} | {g['mrr_at_k']:.3f} |")
    lines+=['','## 分组后的test集','', '| 库 | 方法 | 题数 | Hit@K | 已标注Recall@K | MRR@K |','| --- | --- | ---: | ---: | ---: | ---: |']
    for g in summary['groups']:
        if g['split']=='test':lines.append(f"| {g['collection']} | {g['method']} | {g['queries']} | {g['hit_at_k']:.3f} | {g['known_recall_at_k']:.3f} | {g['mrr_at_k']:.3f} |")
    lines+=['','## 边界与停止参照控制','']
    for c in summary['controls']:lines.append(f"- {c['method']}：停止参照泄漏 {c['withdrawn_leak_queries']}/{c['withdrawn_queries']}；无答案或噪声查询仍返回结果 {c['nonempty_no_answer_queries']}/{c['no_answer_queries']}。")
    lines+=['','当前研究检索没有独立拒答阈值。负例的非空结果只表明排序器仍返回候选，不意味着系统能够回答，也不能当作无答案识别正确率。','',
       '## 混合检索未命中或未召回全部已标注来源的题目','']
    for d in details:
        if d['method']=='hybrid' and d['metrics'] is not None and d['metrics']['known_recall_at_k']<1:
            lines.append(f"- {d['query_id']} / {d['split']}：{d['query']}\n  标注：{', '.join(d['known_positives'])}；返回：{', '.join(c['doc_id'] for c in d['candidates'])}")
    lines+=['','## 案例文档命中但指定证据锚点未命中','']
    for d in details:
        if d['method']=='hybrid' and d['collection']=='case' and d['metrics'] is not None and d['metrics']['known_recall_at_k']>d['metrics']['anchor_recall_at_k']:
            lines.append(f"- {d['query_id']}：{d['query']}\n  返回分片：{', '.join(c['fragment_id'] for c in d['candidates'])}；需人工判断是否召回了其他同义论证段。")
    lines+=['','## 混合检索按问法切片','', '| 问法 | 题数 | Hit@K | 已标注Recall@K |','| --- | ---: | ---: | ---: |']
    for s in summary.get('slices',[]):
        if s['field']=='style':lines.append(f"| {s['value']} | {s['queries']} | {s['hit_at_k']:.3f} | {s['known_recall_at_k']:.3f} |")
    lines+=['','问法切片按题汇总法条与案例，各自沿用K=4与K=2；它是描述性统计，不是固定同一个K的跨库比较。']
    lines+=['','## 解读边界','',
       '案例按parent_id计分，同一案例多个分片不会重复加分。锚点指标要求返回分片含指定原句，是严格定位诊断；未含该句不等于片段一定不相关。BM25返回全文，故不与分片方法比较锚点指标。',
       '共享任一qrel来源的题目归入同一split，避免同条法条的改写跨dev/test。定位题只在dev。test为初始保留集；若根据本报告改参数，需记录test已经被使用，并补充新保留集。',
       '没有进行模型自动相关性判分，也没有计算把未标注文档当负例的Precision。题目由本助手及研究任务根据公开原文编写，未经独立法律专家全面评审。',
       '原v1的24条案例题相对容易，其100%命中结果只适用于该种子集；新增题另列cohort统计。来源内的两种问法相互关联，题数不等于独立案件或条文数量，当前指标按题宏平均。',
       f"当前题数：{summary['dataset']['rows']}；唯一标注来源：{summary['dataset'].get('unique_qrel_sources','v1未单列')}。",
       f"数据版本：{summary['dataset']['version']}；数据指纹：{summary['dataset']['dataset_sha256']}；排序重放耗时：{summary['rank_replay_seconds']}秒（不含查询向量API生成）。"]
    if (out/'expansion-regression.json').exists():
        lines+=['','冻结v1原80题三种方法逐题一致，并对16题独立离线重放验证一致、提供方请求数为0；详见 [版本与重放核对](expansion-regression.json)。全量400题完成一次基线，不声称全部400题都重复重放。']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--embed-missing',action='store_true',help='Explicitly call existing embedding API for missing query vectors')
    parser.add_argument('--bm25-only',action='store_true')
    parser.add_argument('--split',choices=['all','dev','test'],default='all')
    parser.add_argument('--dataset',help='Optional dataset directory, e.g. evaluation/archives/retrieval-v1')
    parser.add_argument('--output',help='Optional result directory; archive inputs are never overwritten by default')
    parser.add_argument('--query-ids',help='Optional comma-separated IDs for a fixed replay sample')
    run(parser.parse_args())
