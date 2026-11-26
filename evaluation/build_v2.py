"""Build v2 from the immutable v1 and explicitly source-anchored new seeds."""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from corpus import connection
from evaluation.build_dataset import normalized,digest,corpus_fingerprint
from evaluation.expansion.law_seeds import LAW_PAIRS,SECOND_QUOTES

ROOT=Path(__file__).parent
VERSION='retrieval-v2'

def grouped_splits(rows):
    groups=[]
    for row in rows:
        ids={q['doc_id'] for q in row['qrels']}
        matches=[g for g in groups if g['ids']&ids]
        if matches:
            group=matches[0];group['rows'].append(row);group['ids']|=ids
            for other in matches[1:]:group['ids']|=other['ids'];group['rows']+=other['rows'];groups.remove(other)
        else:groups.append(dict(ids=ids,rows=[row]))
    for group in groups:
        key='|'.join(sorted(group['ids']));split='dev' if int(digest(key)[:8],16)%3==0 else 'test'
        if any(r['style']=='locator' for r in group['rows']):split='dev'
        for row in group['rows']:row.update(split=split,source_group=digest(key)[:12])

def main():
    with connection() as db:docs={key:json.loads(raw) for key,raw in db.execute('SELECT id,payload FROM documents')}
    guides={d['guiding_id']:d for d in docs.values() if d['doc_type']=='case' and d.get('guiding_id')}
    old=[json.loads(line) for name in ('laws','cases','controls') for line in (ROOT/'archives/retrieval-v1'/(name+'.jsonl')).read_text(encoding='utf-8').splitlines()]
    rows=[dict({k:v for k,v in row.items() if k!='version'},cohort='regression_v1',origin_version='retrieval-v1') for row in old]
    def qrel(key,quote,grade=2):
        doc=docs[key]
        if normalized(quote) not in normalized(doc['text']):raise ValueError('Missing anchor '+key+': '+quote)
        if doc.get('reference_status')=='not_reference':raise ValueError('Withdrawn positive')
        return dict(doc_id=key,grade=grade,evidence_quote=quote,title=doc['title'],source_url=doc['url'],text_sha256=digest(doc['text']))
    for i,seed in enumerate(LAW_PAIRS):
        key,domain,quote,q1,q2=seed[:5]
        for variant,query in enumerate((q1,q2)):
            labels=[qrel(key,SECOND_QUOTES.get(key,quote) if variant==1 else quote)]
            if variant==1 and len(seed)>5:labels.append(qrel(*seed[5]))
            rows.append(dict(id=f'L{49+i*2+variant:03}',collection='law',query=query,domain=domain,style='scenario' if variant==0 else ('multi_intent' if len(labels)>1 else 'colloquial'),
                cohort='expansion_v2',origin_version=VERSION,qrels=labels,confusable_ids=[],family=f'law-{key}',annotation_scope='本地官方原文锚点核对；非穷尽相关性标注'))
    case_records=[]
    for name in ('case-research-a','case-research-b'):
        text=(ROOT/'expansion'/(name+'.md')).read_text(encoding='utf-8')
        blocks=re.findall(r'```json\s*(.*?)```',text,re.S)
        if len(blocks)!=1:raise ValueError(name+' needs one JSON array')
        records=json.loads(blocks[0])
        if len(records)!=38:raise ValueError(name+' requires 38 new case families')
        case_records.extend(records)
    old_cases={q['doc_id'] for row in old if row['collection']=='case' for q in row['qrels']}
    if len({r['guide'] for r in case_records})!=76:raise ValueError('Repeated new guide')
    for i,record in enumerate(sorted(case_records,key=lambda r:r['guide'])):
        doc=guides[record['guide']]
        if doc['id'] in old_cases or record['source_url']!=doc['url']:raise ValueError('New source overlap or URL mismatch')
        if not 12<=len(normalized(record['quote']))<=80:raise ValueError('Case anchor length')
        if len(record['queries'])!=2:raise ValueError('Need two distinct case queries')
        for variant,query in enumerate(record['queries']):
            if query['style'] not in ('scenario','colloquial','contrast'):raise ValueError('Unknown case style')
            if re.search(r'指导(?:性)?案例\s*\d+',query['text']):raise ValueError('Case locator not allowed in expansion')
            if 'quote' not in query or not 12<=len(normalized(query['quote']))<=80:raise ValueError('Need query-specific evidence anchor')
            rows.append(dict(id=f'C{25+i*2+variant:03}',collection='case',query=query['text'],domain=record['domain'],style=query['style'],
                cohort='expansion_v2',origin_version=VERSION,qrels=[qrel(doc['id'],query['quote'])],confusable_ids=[],family=f'case-{record["guide"]}',
                annotation_scope='依据指导案例发布文本编写，含原文引用；非独立专家相关性评审'))
    absent_laws=['中华人民共和国刑法','中华人民共和国行政诉讼法','中华人民共和国行政处罚法','中华人民共和国证券法','中华人民共和国著作权法','中华人民共和国专利法','中华人民共和国企业破产法','中华人民共和国行政复议法']
    present={d.get('law_name') for d in docs.values()}
    if present&set(absent_laws):raise ValueError('Out-of-corpus control is now in corpus')
    controls=[dict(query='只检索《'+name+'》的完整条文，不要相关案例或其他法律',collection='law',style='out_of_corpus',reason='当前法条库未收录'+name,forbidden_ids=[]) for name in absent_laws]
    for number in (123,136,139,204):
        doc=guides[number]
        if doc.get('reference_status')!='not_reference':raise ValueError('Withdrawal status changed')
        controls.append(dict(query='查找'+doc['title'],collection='case',style='withdrawn',reason='已公告停止参照的案例不得进入研究召回',forbidden_ids=[doc['id']]))
    controls += [dict(query='qvzx_no_semantic_target_314159',collection='law',style='noise',reason='无语义查询',forbidden_ids=[]),
        dict(query='zqvx_no_semantic_target_271828',collection='case',style='noise',reason='无语义查询',forbidden_ids=[]),
        dict(query='只查找个人信息保护法第9999条原文',collection='law',style='out_of_corpus',reason='当前该法仅74条',forbidden_ids=[]),
        dict(query='只查找指导案例99999号的发布原文',collection='case',style='out_of_corpus',reason='当前库不存在该编号',forbidden_ids=[])]
    for i,control in enumerate(controls,9):rows.append(dict(id=f'N{i:03}',domain='边界控制',split='control',qrels=[],cohort='expansion_v2',origin_version=VERSION,**control))
    positives=[r for r in rows if r['qrels']];grouped_splits(positives)
    old_by_id={r['id']:r for r in old}
    for row in rows:
        if row['id'] in old_by_id:
            original=old_by_id[row['id']]
            if any(row.get(key)!=value for key,value in original.items() if key!='version'):raise ValueError('Original v1 row or split changed: '+row['id'])
    keys=[re.sub(r'[^\w\u4e00-\u9fff]','',r['query']).lower() for r in rows]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate or punctuation-only variation')
    if len(rows)!=400:raise ValueError('Expected 400 questions')
    ordered=[r for kind in ('law','case','control') for r in rows if (r['split']=='control' if kind=='control' else r['collection']==kind and r['split']!='control')]
    for name,kind in [('laws','law'),('cases','case'),('controls','control')]:
        subset=[r for r in ordered if (r['split']=='control' if kind=='control' else r['collection']==kind and r['split']!='control')]
        (ROOT/(name+'.jsonl')).write_text(''.join(json.dumps(dict(version=VERSION,**r),ensure_ascii=False)+'\n' for r in subset),encoding='utf-8')
    unique={kind:len({q['doc_id'] for r in positives if r['collection']==kind for q in r['qrels']}) for kind in ('law','case')}
    manifest=dict(version=VERSION,rows=len(rows),laws=200,cases=176,controls=24,dataset_sha256=digest(json.dumps(ordered,ensure_ascii=False,sort_keys=True)),
        corpus_sha256=corpus_fingerprint(docs),corpus_counts={kind:sum(d['doc_type']==kind for d in docs.values()) for kind in ('law','case')},
        split_counts={s:sum(r['split']==s for r in rows) for s in ('dev','test','control')},cohort_counts={c:sum(r['cohort']==c for r in rows) for c in ('regression_v1','expansion_v2')},
        unique_qrel_sources=unique,labeling='原文锚点校验与来源核对，未经独立法律专家穷尽相关性评审；查询非被测语言模型生成，未使用自动模型评分',
        split_policy='保留v1全部原题和分组；共享任一qrel的查询按来源连通分量分组，dev/test无qrel交集。新增题由同一来源两种问法构成，题数不能当作独立来源数。新题单独标记expansion_v2。')
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    near=[]
    families={r.get('family') for r in rows if r.get('family')}
    for family in sorted(families):
        pair=[r for r in rows if r.get('family')==family]
        similarity=SequenceMatcher(None,pair[0]['query'],pair[1]['query']).ratio()
        if similarity>=.85:near.append(dict(family=family,ids=[r['id'] for r in pair],similarity=round(similarity,3)))
    audit=dict(unique_queries=len(set(keys)),unique_sources=unique,near_duplicate_family_pairs=near,
        original_rows_unchanged=True,all_qrel_anchors_match=True,new_case_families=76,new_law_families=76,
        query_specific_case_anchors=True,law_second_query_anchor_overrides=len(SECOND_QUOTES),
        seed_files_sha256={name:digest((ROOT/name).read_text(encoding='utf-8')) for name in ('expansion/law_seeds.py','expansion/case-research-a.md','expansion/case-research-b.md')},
        repeated_source_notice='来源内两种问法相关，不能按400个独立案件计算统计置信度')
    (ROOT/'quality-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__':main()
