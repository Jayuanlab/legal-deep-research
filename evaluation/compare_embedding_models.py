"""Compare model-specific baselines on an identical frozen dataset/corpus."""
import json
from pathlib import Path

ROOT=Path(__file__).parent

def main():
    old=json.loads((ROOT/'results/summary.json').read_text(encoding='utf-8'))
    new=json.loads((ROOT/'results-aliyun/summary.json').read_text(encoding='utf-8'))
    for field in ('dataset_sha256','corpus_sha256'):
        if old['dataset'][field]!=new['dataset'][field]:raise ValueError('Baseline snapshots differ: '+field)
    if old['embedding_identity']==new['embedding_identity']:raise ValueError('Embedding identities did not change')
    old_rows=[json.loads(line) for line in (ROOT/'results/details.jsonl').read_text(encoding='utf-8').splitlines()]
    new_rows=[json.loads(line) for line in (ROOT/'results-aliyun/details.jsonl').read_text(encoding='utf-8').splitlines()]
    a={(r['query_id'],r['method']):r for r in old_rows};b={(r['query_id'],r['method']):r for r in new_rows}
    if a.keys()!=b.keys() or len(b)!=1200:raise ValueError('Need full 400-query three-method baselines')
    for key,row in a.items():
        if row['query']!=b[key]['query']:raise ValueError('Question changed')
        if key[1]=='bm25' and (row['candidates']!=b[key]['candidates'] or row['metrics']!=b[key]['metrics']):raise ValueError('BM25 control changed')
    groups=[];lookup={(g['collection'],g['method']):g for g in old['groups'] if g['split']=='all'}
    lines=['# Jina与阿里云向量模型同题对比','',
       '同一retrieval-v2的400题、同一法条/案例快照、相同分片、BM25、RRF及配额；只更换向量端点/模型及其查询向量。BM25的400题候选与指标已逐题核对一致。','',
       '| 库 / K | 方法 | Jina已标注Recall@K | 阿里云已标注Recall@K | Jina MRR@K | 阿里云 MRR@K | 阿里云锚点Recall@K |',
       '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for g in new['groups']:
        if g['split']!='all':continue
        previous=lookup[(g['collection'],g['method'])]
        groups.append(dict(collection=g['collection'],method=g['method'],before=previous,after=g))
        anchor='—' if g['anchor_recall_at_k'] is None else f"{g['anchor_recall_at_k']:.3f}"
        lines.append(f"| {g['collection']} / {g['k']} | {g['method']} | {previous['known_recall_at_k']:.3f} | {g['known_recall_at_k']:.3f} | {previous['mrr_at_k']:.3f} | {g['mrr_at_k']:.3f} | {anchor} |")
    lines+=['','Jina模型为jina-embeddings-v3；阿里云模型为text-embedding-v4，均为1024维，但属于不同向量空间，全部文档向量和400条查询向量分别建立，未复用旧向量。',
       '标签是基于官方存档的部分相关性标注，未获独立专家穷尽评审。案例命中不等于关键分片命中，更不代表法律回答正确。此结果不衡量提供方长期稳定性，也不把一次运行耗时解释为网络性能结论。',
       '[Jina原基线](results/report.md)；[阿里云新基线](results-aliyun/report.md)。']
    (ROOT/'embedding-model-comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    record=dict(dataset_sha256=new['dataset']['dataset_sha256'],corpus_sha256=new['dataset']['corpus_sha256'],queries=400,
        before_identity=old['embedding_identity'],after_identity=new['embedding_identity'],bm25_query_results_identical=400,groups=groups)
    (ROOT/'embedding-model-comparison.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(queries=400,bm25_identical=400,groups=[dict(collection=g['collection'],method=g['method'],old_recall=g['before']['known_recall_at_k'],new_recall=g['after']['known_recall_at_k']) for g in groups]),ensure_ascii=False))

if __name__=='__main__':main()
