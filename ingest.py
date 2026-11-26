import hashlib
import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from corpus import DATA,rebuild


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag in ('p','div','br','li','h1','h2','h3'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('p','div','li'): self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip: self.parts.append(data)


def cn_number(value):
    digits=dict(zip('零一二三四五六七八九',range(10)))
    total=current=0
    for char in value:
        if char in digits: current=digits[char]
        elif char in '十百千': total+=(current or 1)*{'十':10,'百':100,'千':1000}[char]; current=0
        else: raise ValueError('无法解析条号')
    return total+current


def extract_articles(html):
    parser=TextParser(); parser.feed(html)
    text=''.join(parser.parts).replace('\xa0',' ')
    matches=list(re.finditer(r'(?:^|\n)[ \t\u3000]*第([零一二三四五六七八九十百千]+)条[ \t\u3000]+',text))
    result={}
    for i,m in enumerate(matches):
        body=text[m.start():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
        # Section headings between articles are not part of the preceding article.
        body=re.split(r'\n\s*(?:第[零一二三四五六七八九十百千]+[章节编分]|[一二三四五六七八九十]+、)',body)[0].strip()
        body=re.split(r'\n\s*(?:责任编辑|来源：|地址：|相关链接)',body)[0].strip()
        body='\n'.join(line.strip() for line in body.splitlines() if line.strip())
        result[cn_number(m.group(1))]=body
    return result


SOURCES=[
    dict(key='civil-code',url='https://www.court.gov.cn/zixun/xiangqing/233181.html',title='中华人民共和国民法典',effective='2021-01-01',published='2020-05-28',start=1,end=1260,offset=0,version='2020年通过文本'),
    dict(key='contract-interpretation',url='https://www.court.gov.cn/fabu/xiangqing/419382.html',title='最高人民法院关于适用《中华人民共和国民法典》合同编通则若干问题的解释',effective='2023-12-05',published='2023-12-04',start=1,end=69,offset=10000,version='法释〔2023〕13号'),
]


def civil_topic(number):
    for end,name in [(204,'总则'),(462,'物权'),(988,'合同'),(1039,'人格权'),(1118,'婚姻家庭'),(1163,'继承'),(1258,'侵权责任'),(1260,'附则')]:
        if number<=end:return name


def main(refresh=False):
    DATA.mkdir(exist_ok=True); (DATA/'raw').mkdir(exist_ok=True)
    docs=[]; manifest=[]
    for source in SOURCES:
        path=DATA/'raw'/(source['key']+'.html')
        if refresh:
            req=urllib.request.Request(source['url'],headers={'User-Agent':'LegalResearchDemo/0.2 (local educational corpus)'})
            with urllib.request.urlopen(req,timeout=45) as response:
                raw=response.read(); encoding=response.headers.get_content_charset() or 'utf-8'
        else:
            raw=path.read_bytes();encoding='utf-8'
        html=raw.decode(encoding)
        articles=extract_articles(html)
        required=set(range(source['start'],source['end']+1))
        missing=required-set(articles)
        if missing: raise ValueError(f"{source['key']}: 缺少条文 {sorted(missing)}，停止写入")
        digest=hashlib.sha256(raw).hexdigest()
        if refresh:path.write_bytes(raw)
        stamp=datetime.now(timezone.utc).isoformat()
        for number in sorted(required):
            text=articles[number]
            if source['key']=='contract-interpretation' and number==69:
                text=re.split(r'\n(?:责任编辑|来源|相关|最高人民法院)',text)[0]
            docs.append(dict(id='E'+str(source['offset']+number),doc_type='law',article=str(number),
                title=f"{source['title']} 第{number}条",text=text,tags='民法典 '+civil_topic(number) if source['offset']==0 else '合同 司法解释',url=source['url'],
                law_name=source['title'],topic=civil_topic(number) if source['offset']==0 else '合同',
                kind='法律原文' if source['offset']==0 else '司法解释原文',date=source['effective'],
                published_at=source['published'],version=source['version'],retrieved_at=stamp,source_sha256=digest,
                text_sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                authority_status='来源发布版本；当前效力及个案时间适用待核验'))
        manifest.append(dict(source,sha256=digest,retrieved_at=stamp,articles=len(required)))
    (DATA/'laws.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
    (DATA/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(rebuild(),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true',help='Download official source pages; default uses local archives only.')
    main(parser.parse_args().refresh)
