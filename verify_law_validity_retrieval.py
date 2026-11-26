import json,time
import corpus,vectors
from official_bulk import dump
question='根据现行规则，建设工程施工合同无效但工程验收合格，承包人还能请求折价补偿吗？'
start=time.monotonic();rows=vectors.retrieve(question)
rules=json.loads((corpus.DATA/'law-validity.json').read_text(encoding='utf-8'))['by_id']
forbidden={k for k,v in rules.items() if v['code'] in ('repealed','superseded','partially_repealed')}
assert len(forbidden)>2000 and rows
assert not forbidden&{d.get('parent_id',d['id']) for d in rows}
assert all(d.get('reference_status')!='not_reference' for d in rows)
assert any(d['doc_type']=='law' for d in rows)
result=dict(query=question,passed=True,seconds=round(time.monotonic()-start,2),excluded_repealed_records=len(forbidden),returned=[dict(id=d['id'],title=d['title'],status=d.get('validity',{}).get('code')) for d in rows],scope='一次真实阿里云查询向量及本地混合召回，检查已确认废止版本不泄漏；不代表全部法律效力已核验。')
dump(corpus.DATA/'validity-all-retrieval-validation.json',result);print(json.dumps(result,ensure_ascii=False))
