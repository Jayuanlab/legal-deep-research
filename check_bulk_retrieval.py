"""Predefined expanded-corpus diagnostics, using real query embeddings and exact spans."""
import argparse,json,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import corpus
from vectors import retrieve
from official_bulk import dump

CHECKS=[
 ('首次违法且危害后果轻微并及时改正，行政处罚法是否允许不予处罚？','中华人民共和国行政处罚法','33'),
 ('行政强制法中，加处罚款或者滞纳金每日计收，累计金额能超过金钱给付义务金额吗？','中华人民共和国行政强制法','45'),
 ('刑法第二百五十三条之一如何规定侵犯公民个人信息罪？','中华人民共和国刑法','253之1'),
 ('刑事诉讼法关于未经人民法院依法判决不得确定任何人有罪的规定。','中华人民共和国刑事诉讼法','12'),
 ('企业破产法规定债权人对债务人不能清偿到期债务能否申请破产清算？','中华人民共和国企业破产法','7'),
 ('安全生产法规定生产经营单位的主要负责人对本单位安全生产工作承担什么责任？','中华人民共和国安全生产法','5'),
 ('行政复议法规定公民申请行政复议的一般期限是多少天？','中华人民共和国行政复议法','20'),
 ('电子商务法对电子商务经营者处理消费者个人信息的义务如何规定？','中华人民共和国电子商务法','23'),
 ('个人申请获取政府信息公开，一般应在多少个工作日内答复？','中华人民共和国政府信息公开条例','33'),
 ('工伤保险条例规定劳动者在工作时间和工作场所内因工作原因受到事故伤害如何认定？','工伤保险条例','14'),
 ('劳动合同法实施条例规定达到法定退休年龄时劳动合同是否终止？','中华人民共和国劳动合同法实施条例','21'),
 ('食品安全法规定生产经营不符合食品安全标准的食品时消费者能否主张十倍价款赔偿？','中华人民共和国食品安全法','148'),
]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--staged',action='store_true');a=p.parse_args()
    if a.staged:corpus.DB=corpus.DATA/'legal-bulk.sqlite3'
    with corpus.connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
    frozen=[]
    for query,name,number in CHECKS:
        expected=[d['id'] for d in docs.values() if d['doc_type']=='law' and d.get('law_name')==name and d.get('article')==number and d.get('reference_status')!='not_reference']
        frozen.append(dict(query=query,expected_ids=expected,kind='law',label_source='人工预先指定规范及条号；未穷尽全部相关法条'))
    # Locator checks are deliberately labeled; they are not scenario generalization scores.
    extra=json.loads((Path(__file__).parent/'data/cases-bulk.json').read_text(encoding='utf-8'))
    selected=[d for d in extra if d.get('points')][:6]
    for d in selected:frozen.append(dict(query=d['title'],expected_ids=[d['id']],kind='case',label_source='案名定位诊断，查询直接使用已存案名'))
    dump(Path(__file__).parent/'evaluation/bulk-smoke-queries.json',frozen)
    def check(row):
        started=time.perf_counter();found=retrieve(row['query']);ids=[d['parent_id'] for d in found if d['doc_type']==row['kind']]
        for d in found:
            original=docs[d['parent_id']];f=d['fragment']
            assert d['text']==original['text'][f['start']:f['end']]
            assert d.get('reference_status')!='not_reference'
        return dict(row,candidates=ids,hit=bool(set(ids)&set(row['expected_ids'])),source_present=bool(row['expected_ids']),exact_spans=True,elapsed=round(time.perf_counter()-started,2))
    # One scan at a time bounds memory as the collection grows.
    results=[]
    for i,row in enumerate(frozen,1):
        r=check(row);results.append(r);print(json.dumps(dict(n=i,total=len(frozen),hit=r['hit'],source_present=r['source_present'],elapsed=r['elapsed'])),flush=True)
    report=dict(queries=len(results),hits=sum(r['hit'] for r in results),rows=results,scope='真实阿里云查询向量与生产RRF检索。12题预先指定法条诊断+6题案名定位，不是完整400题重评或法律回答正确率；保留未命中记录。')
    dump(Path(__file__).parent/'evaluation/bulk-smoke.json',report)
    print(json.dumps(dict(queries=report['queries'],hits=report['hits'])),flush=True)
