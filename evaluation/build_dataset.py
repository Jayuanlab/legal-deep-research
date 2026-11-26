"""Versioned, source-anchored retrieval seeds. No network or LLM labeling."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from corpus import connection

ROOT=Path(__file__).parent
VERSION='retrieval-v1'
# Query, domain, style, [(source ID, grade, exact evidence anchor)], confusable IDs.
LAWS=[
 ('供应商拖着不交货，催了以后还是没交，我能解除合同吗？','合同','colloquial',[('E563',2,'经催告后在合理期限内仍未履行')],['E565']),
 ('依法解除合同，是发出通知就生效，还是对方收到才生效？','合同','contrast',[('E565',2,'合同自通知到达对方时解除')],['E563']),
 ('因对方违约解除合同，已经支付的预付款和损失应如何处理？','合同','scenario',[('E566',2,'可以请求恢复原状或者采取其他补救措施')],[]),
 ('合同里违约金比实际损失高很多，可以请法院往下调吗？','合同','colloquial',[('E585',2,'约定的违约金过分高于造成的损失的'),('E10065',2,'约定的违约金超过造成损失的百分之三十')],[]),
 ('解除采购合同后另找供应商买贵了，替代交易差价按什么规则计算？','合同','scenario',[('E10060',2,'按照替代交易价格与合同价格的差额')],['E585']),
 ('台风导致合同无法履行，免责是否还要及时通知并提供证明？','合同','scenario',[('E590',2,'应当及时通知对方')],['E563']),
 ('本来已经逾期，后来才发生洪水，还能用不可抗力免掉违约责任吗？','合同','contrast',[('E590',2,'当事人迟延履行后发生不可抗力的')],[]),
 ('对方违约后我放着损失继续扩大，扩大的部分也能要求赔偿吗？','合同','colloquial',[('E591',2,'没有采取适当措施致使损失扩大的')],['E584']),
 ('违约损害赔偿是否包括原本能赚到的利润，是否受订约时可预见范围限制？','合同','scenario',[('E584',2,'不得超过违约一方订立合同时预见到')],['E591']),
 ('恶意违约的人请求降低违约金，合同编通则司法解释怎样规定？','合同','term',[('E10065',2,'恶意违约的当事人一方请求减少违约金的')],[]),
 ('逾期交付经催告仍不履行，解除权、通知到达生效以及解除后返还和赔偿分别有什么依据？','合同','multi_intent',[('E563',2,'经催告后在合理期限内仍未履行'),('E565',2,'合同自通知到达对方时解除'),('E566',2,'可以请求恢复原状或者采取其他补救措施')],[]),
 ('东西一直没送来，我催过也没用，这笔买卖能不能不做了？','合同','colloquial',[('E563',2,'经催告后在合理期限内仍未履行')],[]),
 ('上市母公司签字盖章提供担保，我没有根据公开披露的担保决议信息签约，担保对它有约束力吗？','担保','scenario',[('E26009',2,'相对人未根据上市公司公开披露的关于担保事项')],['E26007']),
 ('债权人依据上市公司公开披露的董事会担保决议信息订立保证合同，要求承担责任的专门规定是什么？','担保','term',[('E26009',2,'相对人根据上市公司公开披露的关于担保事项')],[]),
 ('普通公司法定代表人超越权限提供担保，债权人合理审查决议与善意如何判断？','担保','contrast',[('E26007',2,'相对人有证据证明已对公司决议进行了合理审查')],['E26009']),
 ('公司为全资子公司担保的决议例外，能不能直接用到上市公司身上？','担保','contrast',[('E26008',2,'上市公司对外提供担保，不适用前款第二项、第三项')],['E26009']),
 ('公司给自己的股东或实际控制人做担保，谁来表决，关联股东能参与吗？','公司','scenario',[('E22015',2,'公司为公司股东或者实际控制人提供担保的')],['E26007']),
 ('老板违法把我辞了，赔偿金是不是经济补偿标准的两倍，基数怎么算？','劳动','colloquial',[('E20087',2,'经济补偿标准的二倍'),('E20047',2,'解除或者终止前十二个月的平均工资')],['E20046']),
 ('员工工作十一个月，解除劳动合同时经济补偿年限怎样折算？','劳动','scenario',[('E20047',2,'六个月以上不满一年的，按一年计算')],['E20087']),
 ('入职两个月还没签书面劳动合同，双倍工资有什么规定？','劳动','colloquial',[('E20082',2,'超过一个月不满一年未与劳动者订立书面劳动合同')],[]),
 ('签两年劳动合同，试用期最多可以约定几个月？','劳动','scenario',[('E20019',2,'劳动合同期限一年以上不满三年的')],[]),
 ('员工不能胜任工作，培训或调岗后仍不能胜任，解除时提前通知和代通知金如何规定？','劳动','scenario',[('E20040',2,'经过培训或者调整工作岗位，仍不能胜任工作的')],['E20039']),
 ('劳动者严重违反单位规章制度，公司据此解除劳动合同的法律依据是什么？','劳动','term',[('E20039',2,'严重违反用人单位的规章制度的')],['E20040']),
 ('被违法解除后，我可以要求继续履行劳动合同而不是只拿赔偿吗？','劳动','contrast',[('E20048',2,'劳动者要求继续履行劳动合同的')],['E20087']),
 ('固定期限劳动合同到期公司不续签，支付经济补偿的条件有哪些？','劳动','scenario',[('E20046',2,'终止固定期限劳动合同的')],['E20047']),
 ('上市公司一年内对外担保金额超过资产总额三成，需要什么会议和表决比例？','公司','scenario',[('E22135',2,'金额超过公司资产总额百分之三十的')],['E22015']),
 ('董事和实际执行公司事务的控制人，忠实与勤勉义务如何规定？','公司','term',[('E22180',2,'董事、监事、高级管理人员对公司负有忠实义务')],[]),
 ('网上买的普通商品不想要了，七天退货要不要说明理由？','消费者','colloquial',[('E23025',2,'消费者有权自收到商品之日起七日内退货')],[]),
 ('商家欺诈消费者，退一赔三和最低五百元赔偿的依据在哪里？','消费者','colloquial',[('E23055',2,'增加赔偿的金额不足五百元的，为五百元')],[]),
 ('数据受托方想把员工资料再交给另一家公司处理，转委托需取得谁的同意？','个人信息','scenario',[('E25021',2,'未经个人信息处理者同意，受托人不得转委托')],['E25023']),
 ('原来用于提供服务的数据现在想拿去训练模型，改变目的后还要重新同意吗？','个人信息','scenario',[('E25014',2,'处理目的、处理方式和处理的个人信息种类发生变更的'),('E25023',1,'接收方变更原先的处理目的、处理方式的')],['E25021']),
 ('医疗健康和金融账户是不是敏感个人信息，处理时是否需要单独同意？','个人信息','multi_intent',[('E25028',2,'医疗健康、金融账户、行踪轨迹'),('E25029',2,'处理敏感个人信息应当取得个人的单独同意')],[]),
 ('我撤回对个人信息处理的同意以后，处理者应当删除数据吗？','个人信息','scenario',[('E25047',2,'个人撤回同意')],['E25014']),
 ('委托外包处理敏感个人信息前，要不要进行个人信息保护影响评估？','个人信息','scenario',[('E25055',2,'应当事前进行个人信息保护影响评估')],['E25021']),
 ('数据处理委托合同终止后，服务商可以继续保留信息副本吗？','个人信息','scenario',[('E25021',2,'应当将个人信息返还个人信息处理者或者予以删除')],['E25047']),
 ('把用户资料提供给另一家独立的信息处理者时，告知接收方和单独同意有哪些要求？','个人信息','contrast',[('E25023',2,'应当向个人告知接收方的名称或者姓名')],['E25021']),
 ('用户以前同意收集信息，新用途上线后是否自动沿用原同意？','个人信息','colloquial',[('E25014',2,'应当重新取得个人同意')],[]),
 ('别人不断骚扰我的私人生活，隐私权保护是否包括生活安宁？','民法人格权','scenario',[('E1032',2,'自然人的私人生活安宁')],['E1034']),
 ('姓名、电话号码和健康信息能识别个人，民法典如何界定个人信息？','民法人格权','term',[('E1034',2,'能够单独或者与其他信息结合识别特定自然人')],['E1032']),
 ('离婚争抚养权，孩子已经满八岁，法院要不要尊重他的真实意愿？','婚姻家庭','scenario',[('E1084',2,'子女已满八周岁的，应当尊重其真实意愿')],['E1079']),
 ('没有遗嘱时配偶子女父母和兄弟姐妹，谁先继承遗产？','继承','colloquial',[('E1127',2,'第一顺序：配偶、子女、父母')],[]),
 ('一般过错侵权责任和推定过错时的举证责任有什么依据？','侵权','term',[('E1165',2,'其不能证明自己没有过错的，应当承担侵权责任')],['E1198']),
 ('商场没有做好安全保障导致顾客受伤，经营者责任是什么？','侵权','scenario',[('E1198',2,'未尽到安全保障义务，造成他人损害的')],['E1165']),
 ('民法典第188条关于一般诉讼时效及最长权利保护期间的原文','民法总则','locator',[('E188',2,'诉讼时效期间为三年')],[]),
 ('约定违背公序良俗，民事法律行为效力如何规定？','民法总则','term',[('E153',2,'违背公序良俗的民事法律行为无效')],[]),
 ('夫妻因感情不和分居两年，调解无效时是否应当准予离婚？','婚姻家庭','scenario',[('E1079',2,'因感情不和分居满二年')],['E1084']),
 ('发现平台保存的个人信息有错误，可以要求更正吗？','民法人格权','scenario',[('E1037',2,'有权提出异议并请求及时采取更正等必要措施')],['E25047']),
 ('定制商品、鲜活易腐食品也都能网购七天无理由退货吗？','消费者','contrast',[('E23025',2,'消费者定作的')],[]),
]

# Guide number, paraphrased retrieval scenario, exact point anchor, domain.
CASES=[
 (1,'房源同时在多家中介挂牌，买方从公开渠道获得同一房源并选择另一家中介，找关于是否跳单的案例。','买方通过其他公众可以获知的正当途径','合同'),
 (15,'几家关联企业人员业务和财务混同，财产无法区分，债权人要求关联公司连带清偿，有什么类似案例？','关联公司人格混同','公司'),
 (24,'交通事故受害人本身没有过错，只因体质特殊伤得更重，能否据此减轻侵权责任的案例。','其体质状况对损害后果的影响','侵权'),
 (53,'污水处理特许经营收益用于应收账款质押，质权人如何优先受偿，找相关指导案例。','特许经营权的收益权可以质押','担保'),
 (57,'多份最高额保证合同中，具体贷款只列出其中一部分，没列出的保证人是否仍负责任的类似案例。','未列明的最高额担保合同的担保人','担保'),
 (67,'分期付股权转让款逾期，能否直接套用分期付款买卖欠款五分之一的解除规则？找股权转让案例。','股权转让人要求解除双方签订的股权转让合同','合同'),
 (68,'企业借贷诉讼中双方可能串通虚构债务，法院如何主动调查并识别虚假诉讼的案例。','虚构事实、恶意串通','程序'),
 (72,'借款双方真实协商终止借贷，把本息清算后转成购房款，区别于以房担保的案例。','将借款本金及利息转化为已付购房款','合同'),
 (89,'父母只因个人喜好给孩子创造全新姓氏，户籍登记机关不予登记，有没有相关案例？','仅凭个人喜好和愿望','行政'),
 (90,'司机在人行横道前遇行人停留也没有让行，交通处罚被起诉，找礼让行人的行政案例。','应当主动停车让行','行政'),
 (95,'把最高额抵押设立前的旧债权纳入担保范围，没有办变更登记，抵押效力如何的案例。','未对该最高额抵押权办理变更登记手续','担保'),
 (107,'国际货物买卖交货有瑕疵但合理努力后仍可使用或转售，是否构成CISG根本违约的案例。','只要买方经过合理努力就能使用货物或转售货物','涉外合同'),
 (109,'独立保函欺诈审查能否全面审理基础交易，银行已经善意付款后能否止付反担保函，找对应案例。','应坚持有限及必要原则','担保'),
 (118,'撤销权判决要求受让人返还财产，受让人私下返给债务人后立即被转移，能否继续对受让人执行的案例。','不能认定生效判决已经得到有效履行','执行'),
 (166,'达成债务和解后我解除了财产保全，对方又恶意不履行，还请求降低和解违约金，找类似案例。','一方当事人依约申请人民法院解除了保全措施后','合同'),
 (168,'抵押人承诺以房产担保却不办理登记，债权人能否按抵押合同要求违约赔偿，有没有案例？','不影响抵押合同的效力','担保'),
 (180,'公司发出解雇通知后，在诉讼中追加通知里没写的严重违纪理由，找相似劳动争议案例。','超出解除劳动合同通知中载明的依据及事由','劳动'),
 (181,'管理人员收到员工性骚扰投诉却纵容或干扰调查，单位据此解雇管理人员，找相关劳动案例。','管理人员未采取合理措施或者存在纵容性骚扰行为','劳动'),
 (183,'完成全年任务的员工因非自身过错在年终奖发放前离职，能否拿到年终奖的案例。','年终奖发放前离职的劳动者','劳动'),
 (185,'招聘单位按籍贯或性别拒绝求职者，因素与岗位内在要求无关，找平等就业权案例。','基于地域、性别等','劳动'),
 (189,'主播签了独家合作却去其他平台直播，实际损失难确定时如何调整高额违约金的案例。','网络直播行业特点','合同'),
 (265,'软件注册强制用户填写并非基本服务必需的用户画像，也不给拒绝后的其他登录方式，找个人信息案例。','未向用户提供不同意提交相关信息情况下的其他登录方式','个人信息'),
 (266,'先享后付信用服务为评估风险收集必要个人信用信息，已告知并采取最小影响方式，找相关案例。','为提供“先享后付”服务','个人信息'),
 (267,'法院执行要求交付网络平台账号密码，但实名认证仍挂原用户，申请平台协助变更实名的案例。','依法变更有关实名认证信息','执行'),
]

def normalized(text):return ''.join(text.split())
def digest(value):return hashlib.sha256(value.encode('utf-8')).hexdigest()
def corpus_fingerprint(docs):
    return digest(json.dumps([dict(id=key,title=d['title'],text_sha256=digest(d['text']),doc_type=d['doc_type'],tags=d.get('tags'),reference_status=d.get('reference_status')) for key,d in sorted(docs.items())],ensure_ascii=False,sort_keys=True))

def build():
    with connection() as db:docs={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
    guides={d['guiding_id']:d for d in docs.values() if d['doc_type']=='case' and d.get('guiding_id')}
    assert 45 not in guides and 'E9999' not in docs
    assert not any(d.get('law_name') in ('中华人民共和国刑事诉讼法','中华人民共和国税收征收管理法') for d in docs.values())
    assert all(guides[n].get('reference_status')=='not_reference' for n in (9,20))
    rows=[]
    def qrel(key,grade,quote):
        d=docs[key];assert normalized(quote) in normalized(d['text']),(key,quote)
        assert d.get('reference_status')!='not_reference'
        return dict(doc_id=key,grade=grade,evidence_quote=quote,title=d['title'],source_url=d['url'],text_sha256=digest(d['text']))
    for i,(query,domain,style,labels,confusable) in enumerate(LAWS,1):
        rows.append(dict(id=f'L{i:03}',collection='law',query=query,domain=domain,style=style,qrels=[qrel(*x) for x in labels],confusable_ids=confusable,annotation_scope='已核对的相关来源；非穷尽相关性标注'))
    for i,(number,query,quote,domain) in enumerate(CASES,1):
        rows.append(dict(id=f'C{i:03}',collection='case',query=query,domain=domain,style='scenario',qrels=[qrel(guides[number]['id'],2,quote)],confusable_ids=[],annotation_scope='指导案例发布文本的检索相关性，不代表可直接适用当前个案'))
    # Connected qrel components stay in one split, including all paraphrases.
    groups=[]
    for row in rows:
        ids={q['doc_id'] for q in row['qrels']};matches=[g for g in groups if g['ids']&ids]
        if matches:
            group=matches[0];group['rows'].append(row);group['ids']|=ids
            for other in matches[1:]:group['ids']|=other['ids'];group['rows']+=other['rows'];groups.remove(other)
        else:groups.append(dict(ids=ids,rows=[row]))
    for group in groups:
        key='|'.join(sorted(group['ids']));split='dev' if int(digest(key)[:8],16)%3==0 else 'test'
        if any(r['style']=='locator' for r in group['rows']):split='dev'
        for row in group['rows']:row.update(split=split,source_group=digest(key)[:12])
    controls=[
      ('刑事诉讼法第一百七十六条提起公诉的完整条文','law','out_of_corpus',[], '当前法条库未收录刑事诉讼法'),
      ('税收征收管理法关于税收强制执行的完整条文','law','out_of_corpus',[], '当前法条库未收录税收征收管理法'),
      ('仅查找指导案例45号的独立发布原文','case','out_of_corpus',[], '当前独立案例记录缺45号'),
      ('仅查找民法典第9999条原文','law','out_of_corpus',[], '当前民法典仅1至1260条，不存在该记录'),
      ('上海存亮贸易有限公司 蒋志东 王卫明 指导案例9号','case','withdrawn',[guides[9]['id']], '停止参照案例不得进入研究检索'),
      ('深圳市斯瑞曼精细化工 坑梓自来水 指导案例20号','case','withdrawn',[guides[20]['id']], '停止参照案例不得进入研究检索'),
      ('zxqv987654_unsupported_noise','law','noise',[], '无语义噪声，不应被当作具有直接答案'),
      ('qzxv987654_unsupported_noise','case','noise',[], '无语义噪声，不应被当作具有直接答案'),
    ]
    for i,(query,kind,control,forbidden,reason) in enumerate(controls,1):
        rows.append(dict(id=f'N{i:03}',collection=kind,query=query,domain='边界控制',style=control,split='control',qrels=[],forbidden_ids=forbidden,reason=reason))
    assert len(LAWS)==48 and len(CASES)==24 and len(rows)==80
    for name,items in [('laws',[r for r in rows if r['id'].startswith('L')]),('cases',[r for r in rows if r['id'].startswith('C')]),('controls',[r for r in rows if r['id'].startswith('N')])]:
        (ROOT/(name+'.jsonl')).write_text(''.join(json.dumps(dict(version=VERSION,**r),ensure_ascii=False)+'\n' for r in items),encoding='utf-8')
    fingerprint=digest(json.dumps(rows,ensure_ascii=False,sort_keys=True))
    manifest=dict(version=VERSION,rows=len(rows),laws=len(LAWS),cases=len(CASES),controls=len(controls),dataset_sha256=fingerprint,
        corpus_sha256=corpus_fingerprint(docs),
        corpus_counts={kind:sum(d['doc_type']==kind for d in docs.values()) for kind in ('law','case')},
        split_counts={s:sum(r['split']==s for r in rows) for s in ('dev','test','control')},
        labeling='依据本地官方原文逐条编写和锚点校验，未经独立法律专家穷尽标注；未由被测模型自动打分',
        split_policy='共享任一相关来源的查询按连通分量分组，dev/test不共享qrel；定位题仅在dev。test是初始保留集，查看本次基线后若用于调参必须标记已使用。')
    (ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__':
    existing=ROOT/'manifest.json'
    if existing.exists() and json.loads(existing.read_text(encoding='utf-8'))['version']!=VERSION:
        raise SystemExit('Current dataset is newer; use evaluation/build_v2.py. Original v1 is frozen in evaluation/archives/retrieval-v1.')
    build()
