"""Offline inventory and provenance checks. Never fetch remote sources."""
import hashlib
import json
from collections import Counter
from datetime import datetime,timezone
from urllib.parse import urlparse
from corpus import DATA,stats


def audit():
    laws=json.loads((DATA/'laws.json').read_text(encoding='utf-8'))
    extra=DATA/'laws-extra.json'
    if extra.exists():laws+=json.loads(extra.read_text(encoding='utf-8'))
    expansion=DATA/'laws-expansion.json'
    if expansion.exists():laws+=json.loads(expansion.read_text(encoding='utf-8'))
    for name in ('laws-regulations.json','laws-national.json','laws-judicial-bulk.json','laws-gap185.json'):
        path=DATA/name
        if path.exists():laws+=json.loads(path.read_text(encoding='utf-8'))
    cases=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
    typical=DATA/'cases-extra.json'
    if typical.exists():cases+=json.loads(typical.read_text(encoding='utf-8'))
    bulk_cases=DATA/'cases-bulk.json'
    if bulk_cases.exists():cases+=json.loads(bulk_cases.read_text(encoding='utf-8'))
    guiding_extra=DATA/'cases-guiding-extra.json'
    if guiding_extra.exists():cases+=json.loads(guiding_extra.read_text(encoding='utf-8'))
    manifest=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    extra_manifest=DATA/'laws-extra-manifest.json'
    if extra_manifest.exists():manifest+=json.loads(extra_manifest.read_text(encoding='utf-8'))
    expansion_manifest=DATA/'expansion-manifest.json'
    if expansion_manifest.exists():manifest+=[dict(s,law_name=s['name']) for s in json.loads(expansion_manifest.read_text(encoding='utf-8')) if s.get('articles')]
    problems=[]
    ids=[d['id'] for d in laws+cases]
    if len(ids)!=len(set(ids)):problems.append('重复资料编号')
    seen=set();archive_hashes={};archive_safety={};raw_root=(DATA/'raw').resolve()
    for d in laws+cases:
        for field in ('title','text','url','kind','authority_status'):
            if not d.get(field):problems.append(d['id']+' 缺少 '+field)
        if '\ufffd' in d['text'] or '???' in d['title']:problems.append(d['id']+' 编码损坏')
        host=urlparse(d['url']).hostname or ''
        if not (host.endswith('.gov.cn') or host=='81.cn' or host.endswith('.81.cn') or host=='www.12371.cn'):problems.append(d['id']+' 来源不在已审查的官方发布域名范围')
        key=(d.get('law_name'),d.get('version'),d.get('article')) if d['doc_type']=='law' else (d.get('guiding_number') or (d.get('source_collection'),d.get('collection_number')))
        if key in seen:problems.append(d['id']+' 来源主键重复')
        seen.add(key)
        if hashlib.sha256(d['text'].encode()).hexdigest()!=d.get('text_sha256'):
            problems.append(d['id']+' 原文内容哈希不匹配')
        if d.get('raw_path'):
            path=DATA/d['raw_path']
            if path not in archive_safety:archive_safety[path]=path.resolve().is_relative_to(raw_root) and path.exists()
            safe=archive_safety[path]
            if safe and path not in archive_hashes:archive_hashes[path]=hashlib.sha256(path.read_bytes()).hexdigest()
            if not safe or archive_hashes[path]!=d['source_sha256']:
                problems.append(d['id']+' 案例存档校验失败')
    for source in manifest:
        path=DATA.parent/source['raw_path'] if source.get('raw_path') else DATA/'raw'/(source['key']+'.html')
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=(source.get('sha256') or source.get('source_sha256')):
            problems.append(source['key']+' 原始存档校验失败')
    bulk=DATA/'bulk-import-manifest.json'
    if bulk.exists():
        for source in json.loads(bulk.read_text(encoding='utf-8'))['sources']:
            path=DATA/source['raw_path']
            if not path.resolve().is_relative_to((DATA/'raw').resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=source['source_sha256']:
                problems.append(source['key']+' 批量规范存档校验失败')
    # Every law/case raw path was checked above; shared source files are hashed
    # once per audit, with every record still compared to its declared hash.
    civil=[d for d in laws if d.get('law_name')=='中华人民共和国民法典']
    missing=sorted(set(range(1,1261))-{int(d['article']) for d in civil})
    result=dict(generated_at=datetime.now(timezone.utc).isoformat(),network_used=False,counts=stats(),
        law_sources=[dict(title=s.get('title') or s['law_name'],version=s['version'],article_count=s['articles'],source_url=s['url']) for s in manifest],
        civil_code=dict(expected_articles=1260,stored_articles=len(civil),missing_articles=missing),
        topics=dict(Counter(d.get('topic','未分类') for d in laws)),
        case_guides=[dict(id=d['id'],guiding_number=d.get('guiding_number'),case_number=d.get('case_number'),source=d['url']) for d in cases if d.get('guiding_number')],
        typical_cases=[dict(id=d['id'],collection=d['source_collection'],number=d['collection_number'],source=d['url']) for d in cases if d.get('source_collection')],
        problems=problems,scope='检查数据结构、存档哈希与来源记录；不代表现行效力或案例参照状态已核验。',
        withdrawn_cases=[d['guiding_number'] for d in cases if d.get('reference_status')=='not_reference'],
        case_collection=json.loads((DATA/'case-collection.json').read_text(encoding='utf-8')) if (DATA/'case-collection.json').exists() else None,
        bulk_import=json.loads(bulk.read_text(encoding='utf-8')) if bulk.exists() else None,
        national_coverage=json.loads((DATA/'national-coverage.json').read_text(encoding='utf-8')) if (DATA/'national-coverage.json').exists() else None,
        gaps=['303件基准目录标题已存档，版本、效力仍须核验；地方性法规、部门及地方政府规章尚未系统收录，未宣称覆盖全中国法条。','指导案例45号已从山东法院官方转载补齐；指导与典型案例均为发布文本，不等于全国裁判文书全量。','未收录完整法律修订沿革，部分目录或文本解析失败已保留原因，案例停止参照仅核对列明的官方通知。'],
        excluded_local_material='本地 Lawyer LLaMA 目录说明其问答主要由 GPT 生成且未经严格验证，未导入正式法条或裁判案例库。')
    (DATA/'coverage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(counts=result['counts'],civil_missing=len(missing),problems=problems),ensure_ascii=False))
    return result


if __name__=='__main__':
    result=audit()
    if result['problems'] or result['civil_code']['missing_articles']:raise SystemExit(1)
