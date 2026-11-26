"""Small diagnostic for newly imported official sources, using real Aliyun queries."""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import corpus
from vectors import retrieve
from collect_laws_extra import write_json

CHECKS=[
 ('用人单位与劳动者约定不缴纳社会保险费，劳动者能否解除劳动合同并请求经济补偿？','E28019'),
 ('劳动者没有接触商业秘密，劳动合同约定的竞业限制条款是否对他生效？','E28013'),
 ('民间借贷约定利率的司法保护上限是否为合同成立时一年期LPR的四倍？','E30025'),
 ('微信聊天记录、电子邮件和即时通信信息能否作为民事诉讼电子数据？','E29014'),
 ('控制证据的一方无正当理由拒不提交，可以推定该证据对其不利吗？','E29095'),
 ('人脸识别信息处理发生在司法解释2021年8月1日施行前，是否适用该解释？','E33016'),
 ('夫妻离婚协议约定将共同财产给子女，一方能否在转移财产前撤销约定？','E34020'),
 ('实际施工人以发包人为被告主张工程价款，发包人的责任范围如何确定？','E36043'),
 ('民法典施行前的法律事实引起的民事纠纷，应适用哪一时期的法律？','E37001'),
 ('禁止饲养的烈性犬致人损害，饲养人能否主张减轻责任？','E32023'),
 ('找朱某与某保安公司的劳动争议典型案例，约定不缴社保后解除劳动合同经济补偿。','T20006'),
 ('中标通知书到达后拒签书面合同，某物业管理公司与某研究所房屋租赁合同纠纷案。','T20101'),
 ('张某等人因差评被商家擅自公开个人信息，网络侵权责任的典型案例。','T20202'),
 ('马某诉某公司过度收集消费者个人信息，网络服务提供者侵权责任典型案例。','T20305'),
 ('平台代运营商组织虚假交易导致严重违约，平台依约扣除保证金的典型案例。','T20403'),
 ('博某软件公司在维护医院挂号系统时非法获取患者个人信息，侵犯公民个人信息案。','T20501'),
]

def check(item):
    query,target=item;result=retrieve(query)
    with corpus.connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
    for d in result:
        original=docs[d['parent_id']];f=d['fragment']
        assert d['text']==original['text'][f['start']:f['end']]
        assert d.get('reference_status')!='not_reference'
    kind='law' if target.startswith('E') else 'case'
    ids=[d['parent_id'] for d in result if d['doc_type']==kind]
    return dict(query=query,expected=target,collection=kind,candidates=ids,hit=target in ids,exact_spans=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--staged',action='store_true');args=parser.parse_args()
    if args.staged:corpus.DB=corpus.DATA/'legal-next.sqlite3'
    with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(check,CHECKS))
    report=dict(queries=len(rows),hits=sum(r['hit'] for r in rows),rows=rows,
        scope='新增资料的小样本检索诊断，非独立法律专家标注的全面评测，不等同法律回答正确率。全部使用真实阿里云查询向量；原文片段逐一核对。')
    write_json(Path(__file__).parent/'evaluation/expansion-smoke.json',report)
    for r in rows:print(json.dumps(r,ensure_ascii=False),flush=True)
    print(json.dumps(dict(queries=report['queries'],hits=report['hits'])),flush=True)
