"""Offline, reviewed expansion from official archives. Downloads are a separate build step."""
import hashlib,json,re
from bs4 import BeautifulSoup
from collect_laws_extra import DATA, page_text, extract_articles, write_json, sha256, STATUS
from inspect_expansion_sources import SOURCES

LAW_SOURCES=[
 dict(key='labor-i',name='最高人民法院关于审理劳动争议案件适用法律问题的解释（一）',offset=27000,count=54,version='法释〔2020〕26号',published='2020-12-29',effective='2021-01-01',marker='2020年12月25日',topic='劳动争议',tail='本解释自2021年1月1日起施行。'),
 dict(key='labor-ii',name='最高人民法院关于审理劳动争议案件适用法律问题的解释（二）',offset=28000,count=21,version='法释〔2025〕12号',published='2025-07-31',effective='2025-09-01',marker='2025年2月17日',topic='劳动争议',tail='最高人民法院此前发布的司法解释与本解释不一致的，以本解释为准。'),
 dict(key='evidence',name='最高人民法院关于民事诉讼证据的若干规定',offset=29000,count=100,version='2019年修正（法释〔2019〕19号）',published='2019-12-25',effective='2020-05-01',marker='2019年10月14日',topic='民事证据',tail='本规定公布施行后，最高人民法院以前发布的司法解释与本规定不一致的，不再适用。'),
 dict(key='lending',name='最高人民法院关于审理民间借贷案件适用法律若干问题的规定',offset=30000,count=31,version='2020年第二次修正（法释〔2020〕17号）',published='2020-12-29',effective='2021-01-01',marker='2020年12月23日',topic='民间借贷',tail='本规定施行后，最高人民法院以前作出的相关司法解释与本规定不一致的，以本规定为准。',block='关于审理民间借贷案件适用法律若干问题的规定'),
 dict(key='sale',name='最高人民法院关于审理买卖合同纠纷案件适用法律问题的解释',offset=31000,count=33,version='2020年修正（法释〔2020〕17号）',published='2020-12-29',effective='2021-01-01',marker='2020年12月23日',topic='买卖合同',tail='本解释施行后尚未终审的买卖合同纠纷案件，适用本解释；本解释施行前已经终审，当事人申请再审或者按照审判监督程序决定再审的，不适用本解释。',block='关于审理买卖合同纠纷案件适用法律问题的解释'),
 dict(key='tort-i',name='最高人民法院关于适用《中华人民共和国民法典》侵权责任编的解释（一）',offset=32000,count=26,version='法释〔2024〕12号',published='2024-09-25',effective='2024-09-27',marker='2023年12月18日',topic='侵权责任',tail='本解释施行前已经终审，当事人申请再审或者按照审判监督程序决定再审的，适用当时的法律、司法解释规定。'),
 dict(key='face',name='最高人民法院关于审理使用人脸识别技术处理个人信息相关民事案件适用法律若干问题的规定',offset=33000,count=16,version='法释〔2021〕15号',published=None,effective='2021-08-01',marker='2021年6月8日',topic='个人信息保护',tail='信息处理者使用人脸识别技术处理人脸信息、处理基于人脸识别技术生成的人脸信息的行为发生在本规定施行前的，不适用本规定。'),
 dict(key='family-ii',name='最高人民法院关于适用《中华人民共和国民法典》婚姻家庭编的解释（二）',offset=34000,count=23,version='法释〔2025〕1号',published='2025-01-15',effective='2025-02-01',marker='2024年11月25日',topic='婚姻家庭',tail='本解释自2025年2月1日起施行。'),
 dict(key='family-i',name='最高人民法院关于适用《中华人民共和国民法典》婚姻家庭编的解释（一）',offset=35000,count=91,version='法释〔2020〕22号',published='2020-12-29',effective='2021-01-01',marker='2020年12月25日',topic='婚姻家庭',tail='本解释自2021年1月1日起施行。'),
 dict(key='construction',name='最高人民法院关于审理建设工程施工合同纠纷案件适用法律问题的解释（一）',offset=36000,count=45,version='法释〔2020〕25号',published='2020-12-29',effective='2021-01-01',marker='2020年12月25日',topic='建设工程',tail='本解释自2021年1月1日起施行。'),
 dict(key='time-effect',name='最高人民法院关于适用《中华人民共和国民法典》时间效力的若干规定',offset=37000,count=28,version='法释〔2020〕15号',published='2020-12-29',effective='2021-01-01',marker='2020年12月14日',topic='法律时间效力',tail='本规定施行后，人民法院尚未审结的一审、二审案件适用本规定。'),
]
CASE_SOURCES=[
 dict(key='labor-cases',count=6,offset=20000,topic='劳动争议'),
 dict(key='contract-cases',count=10,offset=20100,topic='合同'),
 dict(key='consumer-2023',count=10,offset=20200,topic='消费者权益'),
 dict(key='consumer-2025',count=5,offset=20300,topic='消费者权益'),
 dict(key='platform-2026',count=5,offset=20400,topic='平台经营'),
 dict(key='privacy-cases',count=5,offset=20500,topic='个人信息保护（刑事）'),
]

def archive(key):
    path=DATA/'raw'/('expansion-'+key+'.html')
    raw=path.read_bytes();meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    if meta['url']!=SOURCES[key] or sha256(raw)!=meta['source_sha256']:raise ValueError('Archive mismatch: '+key)
    host=__import__('urllib.parse',fromlist=['urlparse']).urlparse(meta.get('final_url') or meta['url']).hostname
    if host!='court.gov.cn' and not host.endswith('.court.gov.cn'):raise ValueError('Nonofficial redirect')
    soup=BeautifulSoup(raw.decode(meta['encoding']),'html.parser');body=soup.select_one('.txt_txt')
    if body is None:raise ValueError('Missing official body: '+key)
    text='\n'.join(x.strip() for x in page_text(str(body)).splitlines() if x.strip())
    if '\ufffd' in text or '???' in text:raise ValueError('Corrupt text')
    return raw,meta,text,path

def law_articles(s,text):
    if s.get('block'):
        start=text.index('\n'+s['block']+'\n');text=text[start:]
        end=text.find('\n最高人民法院\n',5)
        if end!=-1:text=text[:end]
    # Reuse the checked article parser, with no network and an exact selected block.
    from html import escape
    selected='<div>'+escape(text).replace('\n','<br>')+'</div>'
    return extract_articles(selected,dict(key=s['key'],count=s['count'],version_marker=s['marker'],final_tail=s['tail']))

def case_records(s,text):
    # Prefer standalone body headings; directory entries have no standalone number.
    standalone=list(re.finditer(r'^案例([一二三四五六七八九十0-9]+)\s*$',text,re.M))
    pattern=r'^案例([一二三四五六七八九十0-9]+)[：:、][^\n]+$'
    matches=standalone or list(re.finditer(pattern,text,re.M))
    if len(matches)!=s['count']:raise ValueError(f"{s['key']}: expected {s['count']} case bodies, got {len(matches)}")
    from collect_laws_extra import cn_number
    if [int(m[1]) if m[1].isdigit() else cn_number(m[1]) for m in matches]!=list(range(1,s['count']+1)):raise ValueError('Case number order')
    docs=[]
    for i,m in enumerate(matches):
        start=m.start();end=matches[i+1].start() if i+1<len(matches) else len(text)
        body=text[start:end].strip()
        parts=list(re.finditer(r'【([^】]+)】',body))
        sections={p[1]:body[p.end():parts[j+1].start() if j+1<len(parts) else len(body)].strip() for j,p in enumerate(parts)}
        facts=sections.get('基本案情') or sections.get('简要案情');holding=sections.get('裁判结果') or sections.get('裁判情况')
        reasoning=sections.get('裁判理由') or sections.get('判决理由')
        combined=sections.get('具体内容','')
        complete=(facts and (holding or reasoning)) or (s['key']=='platform-2026' and '法院' in combined and '判' in combined)
        if not complete or len(body)<250:raise ValueError('Incomplete case: '+s['key']+str(i+1))
        title=body[:parts[0].start()].replace('\n',' ').strip()
        docs.append(dict(number=i+1,text=body,title=title,source_start=start,source_end=start+len(body),facts=facts,holding=holding,
                         points=sections.get('裁判要点') or sections.get('典型意义'),reasoning=reasoning,sections=sections))
    return docs

def main():
    laws=[];cases=[];manifest=[]
    for s in LAW_SOURCES+CASE_SOURCES:
        raw,meta,text,path=archive(s['key'])
        common=dict(url=meta['url'],retrieved_at=meta['retrieved_at'],source_sha256=sha256(raw),raw_path=path.relative_to(DATA).as_posix(),topic=s['topic'])
        if 'name' in s:
            rows=law_articles(s,text)
            for n,body in rows.items():
                d=dict(common,id='E'+str(s['offset']+n),doc_type='law',kind='司法解释原文',law_name=s['name'],article=str(n),
                       title=f"{s['name']} 第{n}条",text=body,text_sha256=sha256(body.encode()),version=s['version'],date=s['effective'],
                       published_at=s['published'],tags=s['topic']+' '+s['name'],authority_status=STATUS)
                if s['key']=='labor-i':
                    d['authority_status']+='；解释（二）自2025-09-01施行，不一致之处以解释（二）为准。'
                    if n==32:
                        d.update(reference_status='not_reference',authority_status='本条第一款自2025-09-01被法释〔2025〕12号第二十一条废止；其余款未由该条宣布废止。为避免误用，整条历史发布文本默认不参与研究检索。',status_source=SOURCES['labor-ii'],status_effective='2025-09-01')
                laws.append(d)
        else:
            soup=BeautifulSoup(raw.decode(meta['encoding']),'html.parser')
            date_match=re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})',page_text(str(soup)))
            if not date_match:raise ValueError('Publication date missing: '+s['key'])
            rows=case_records(s,text)
            for row in rows:
                n=row.pop('number');body=row['text']
                cases.append(dict(common,**row,id='T'+str(s['offset']+n),doc_type='case',kind='最高人民法院典型案例发布原文（非指导案例、非判决全文）',
                     source_collection=s['key'],collection_number=n,date=date_match[1],tags=s['topic'],text_sha256=sha256(body.encode()),
                     case_number=None,case_numbers=list(dict.fromkeys(re.findall(r'[（(]\d{4}[）)][\u4e00-\u9fff\d]{1,30}号',body))),court=None,
                     authority_status='最高人民法院官方典型案例发布存档；不等同指导案例效力，个案时间适用待核验',
                     historical_law_note='典型案例所载裁判适用法可能为历史版本；刑事案件不得直接用于认定民事责任，仍须核对本案事实与适用规则。'))
        manifest.append(dict(s,**meta,raw_path=path.relative_to(DATA.parent).as_posix(),articles=len(rows) if 'name' in s else 0,cases=len(rows) if 'name' not in s else 0))
        print(s['key'],len(rows),flush=True)
    for rows in (laws,cases):
        assert len({d['id'] for d in rows})==len(rows)
    # Write only after every source passed structural checks.
    write_json(DATA/'laws-expansion.json',laws);write_json(DATA/'cases-extra.json',cases);write_json(DATA/'expansion-manifest.json',manifest)
    print(json.dumps(dict(laws=len(laws),cases=len(cases)),ensure_ascii=False))

if __name__=='__main__':main()
