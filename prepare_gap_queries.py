import json
from official_bulk import ROOT,dump
docs=json.loads((ROOT/'data/laws-gap185.json').read_text(encoding='utf-8'))
queries=[
 ('中华人民共和国国籍法','中国公民自愿加入外国国籍后，是否自动丧失中国国籍？','自愿加入或取得外国国籍'),
 ('中华人民共和国学位法','学位论文被认定存在代写、剽窃、伪造等学术不端，已取得的学位可以撤销吗？','代写'),
 ('中华人民共和国反外国制裁法','个人配合外国对中国公民采取歧视性限制措施，受损者可以要求停止侵害并赔偿损失吗？','停止侵害'),
 ('中华人民共和国民族区域自治法','民族自治地方能否依照民族特点制定自治条例和单行条例？','自治条例和单行条例'),
 ('中华人民共和国海警法','海警处理海上暴力犯罪时，什么情况下可以使用武器？','使用武器'),
 ('中华人民共和国资源税法','开采原油过程中用于加热的原油是否免征资源税？','加热'),
 ('中华人民共和国农村土地承包法','承包期内，发包方能否随意调整农民承包的土地？','不得调整承包地'),
 ('中华人民共和国公证法','经过公证的民事法律行为、事实和文书，法院应否作为认定事实的根据？','认定事实的根据'),
 ('中华人民共和国慈善法','慈善组织开展公开募捐应取得什么资格？','公开募捐资格'),
 ('中华人民共和国国家安全法','公民和组织发现危害国家安全的活动，是否负有及时报告的义务？','及时报告危害国家安全活动'),
 ('中华人民共和国银行业监督管理法','银行业金融机构严重违反审慎经营规则，监管机构可以采取哪些措施？','严重违反审慎经营规则'),
 ('全国人民代表大会常务委员会关于中国人民解放军现役士兵衔级制度的决定','军士军衔分为哪三等七衔，义务兵军衔有哪些？','三等七衔'),
 ('全国人民代表大会常务委员会关于在沿海港口城市设立海事法院的决定','海事法院是否受理刑事案件和其他民事案件，由哪个机关决定设置或者撤销？','不受理刑事案件'),
]
rows=[]
for name,q,anchor in queries:
 matches=[d for d in docs if d['law_name']==name and anchor in d['text'] and d.get('reference_status')!='not_reference']
 if not matches:raise ValueError((name,anchor))
 rows.append(dict(query=q,expected_law=name,expected_ids=[d['id'] for d in matches],anchor=anchor,label_scope='人工预先指定法条锚点，非穷尽相关性标注'))
dump(ROOT/'evaluation/gap185-smoke-queries.json',rows)
print('Prepared',len(rows),'fixed semantic scenarios')
