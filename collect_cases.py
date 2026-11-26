"""Build-time collection of public SPC guiding-case pages; never used by research."""
import argparse
import hashlib
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup
from corpus import DATA
from ingest import TextParser

BASE='https://www.court.gov.cn'
INDEX=BASE+'/shenpan/gengduo/77.html'
CACHE=DATA/'raw'/'guiding-cases'
GUIDE=re.compile(r'^指导(?:性)?案例\s*(\d+)\s*号')
SECTIONS=('关键词','裁判要点','相关法条','基本案情','裁判结果','裁判理由','执行要点','执行情况','执行实施要点','执行结果','执行理由')


def fetch(url,name,refresh):
    path=CACHE/name
    if path.exists() and not refresh:return path.read_bytes()
    if urlparse(url).hostname!='www.court.gov.cn':raise ValueError('Only public SPC pages may be downloaded')
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'LegalResearchLocalCorpus/0.3'})
            with urllib.request.urlopen(request,timeout=35) as response:
                if urlparse(response.url).hostname!='www.court.gov.cn':raise ValueError('Unexpected redirect')
                raw=response.read()
            if len(raw)<1000:raise ValueError('Empty source page')
            path.write_bytes(raw);return raw
        except Exception:
            if attempt==2:raise
            time.sleep(2*(attempt+1))


def sections(text):
    pattern=r'(?:^|\n)[ \t\u3000]*('+ '|'.join(SECTIONS) +r')(?:[ \t\u3000]*\n|[ \t\u3000]+|$)'
    matches=list(re.finditer(pattern,text));result={}
    for i,m in enumerate(matches):
        result[m.group(1)]=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
    return result


def topic(text):
    if text.startswith('刑事'):return '刑事'
    if text.startswith('行政'):return '行政'
    if text.startswith('执行'):return '执行'
    for label,words in [('劳动争议',('劳动','工伤','用工')),('知识产权',('著作权','专利','商标','商业秘密','技术秘密','知识产权')),('婚姻家庭',('离婚','抚养','探望','婚姻')),('继承',('继承','遗嘱')),('人格权',('隐私','个人信息','名誉','肖像')),('侵权责任',('侵权','交通事故','污染')),('合同',('合同','买卖','借款','租赁','违约')),('公司',('公司','股权'))]:
        if any(w in text for w in words):return label
    return '其他'


def parse_case(raw,url,expected,title_hint='',old=None):
    soup=BeautifulSoup(raw,'html.parser')
    node=soup.select_one('.txt_txt');title_node=soup.select_one('.detail > .title')
    if node is None:raise ValueError('No official case body')
    parser=TextParser();parser.feed(str(node))
    text='\n'.join(line.strip() for line in ''.join(parser.parts).replace('\xa0',' ').splitlines() if line.strip())
    title=title_node.get_text(' ',strip=True) if title_node else title_hint
    match=GUIDE.match(title)
    if not match or int(match.group(1))!=expected:raise ValueError('Title and index number mismatch')
    if not re.search(r'指导(?:性)?案例'+str(expected)+r'号',re.sub(r'\s+','',text[:200])):raise ValueError('Case body number mismatch')
    parts=sections(text)
    if len(text)<200 or not (parts.get('裁判要点') or parts.get('执行实施要点')) or not (parts.get('裁判结果') or parts.get('执行情况') or parts.get('执行结果')):
        raise ValueError('Incomplete guiding-case publication')
    head=text[:text.find('关键词') if '关键词' in text else 300]
    date=re.search(r'(20\d{2})年(\d{1,2})月(\d{1,2})日发布',re.sub(r'\s+','',head))
    published=f'{date[1]}-{int(date[2]):02d}-{int(date[3]):02d}' if date else None
    numbers=list(dict.fromkeys(re.findall(r'[（(]\d{4}[）)][\u4e00-\u9fff\d]{1,30}号',re.sub(r'\s+','',parts.get('裁判结果','') or parts.get('执行结果','')))))
    decisions=[]
    result_text=parts.get('裁判结果','') or parts.get('执行结果','')
    decision_pattern=r'([\u4e00-\u9fff]{2,30}(?:人民法院|知识产权法院|互联网法院))于\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日作出\s*([（(]\d{4}[）)][\u4e00-\u9fff\d]{1,30}号)'
    for court,year,month,day,number in re.findall(decision_pattern,re.sub(r'\s+','',result_text)):
        decisions.append(dict(court=court,date=f'{year}-{int(month):02d}-{int(day):02d}',case_number=number))
    meta=old or {}
    return dict(id=meta.get('id','C'+str(1000+expected)),doc_type='case',title=title,text=text,
        kind='指导案例发布原文（非判决全文）',guiding_number='指导案例'+str(expected)+'号',guiding_id=expected,
        date=published,case_number=meta.get('case_number') or (numbers[0] if len(numbers)==1 else None),
        case_numbers=numbers,decisions=decisions,court=meta.get('court'),facts=parts.get('基本案情'),holding=parts.get('裁判结果') or parts.get('执行情况') or parts.get('执行结果'),
        points=parts.get('裁判要点') or parts.get('执行实施要点'),reasoning=parts.get('裁判理由') or parts.get('执行理由'),related_laws=parts.get('相关法条'),
        tags=parts.get('关键词',''),topic=topic(parts.get('关键词','')+' '+title),url=url,
        historical_law_note='发布文本中的裁判适用法可能为历史版本；不得直接视为当前案件适用法。当前参照及停止参照状态未全量核验。',
        authority_status='官方发布原文存档；当前参照状态及个案适用待核验',
        retrieved_at=datetime.now(timezone.utc).isoformat(),source_sha256=hashlib.sha256(raw).hexdigest(),
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),raw_path='raw/guiding-cases/'+url.rsplit('/',1)[-1])


def main(refresh=False):
    CACHE.mkdir(parents=True,exist_ok=True)
    existing=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
    old={int(re.search(r'\d+',d['guiding_number'])[0]):d for d in existing if d.get('guiding_number')}
    links={};errors=[];lists=[]
    first=fetch(INDEX,'index-1.html',refresh)
    soup=BeautifulSoup(first,'html.parser')
    pages=[int(n) for n in re.findall(r'/shenpan/gengduo/77_(\d+)\.html',str(soup))]
    last=max(pages or [1])
    if last>50:raise ValueError('Unexpected index size')
    for page in range(1,last+1):
        url=INDEX if page==1 else BASE+f'/shenpan/gengduo/77_{page}.html'
        raw=first if page==1 else fetch(url,f'index-{page}.html',refresh)
        lists.append(dict(url=url,sha256=hashlib.sha256(raw).hexdigest()))
        for a in BeautifulSoup(raw,'html.parser').select('a[href]'):
            title=a.get('title') or a.get_text(' ',strip=True)
            match=GUIDE.match(title.strip());href=a['href']
            if match and re.fullmatch(r'/shenpan/xiangqing/\d+\.html',href):
                number=int(match.group(1));links.setdefault(number,(urljoin(BASE,href),title.strip()))
        print(f'Index {page}/{last}: {len(links)} unique case links',flush=True)
    (DATA/'case-download-plan.json').write_text(json.dumps(dict(index=INDEX,pages=lists,cases=[dict(number=n,url=u,title=t) for n,(u,t) in sorted(links.items())]),ensure_ascii=False,indent=2),encoding='utf-8')
    def collect(item):
        number,(url,title)=item
        raw=fetch(url,url.rsplit('/',1)[-1],refresh)
        return parse_case(raw,url,number,title,old.get(number))
    collected={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(collect,item):item[0] for item in links.items()}
        for future in as_completed(futures):
            n=futures[future]
            try:
                collected[n]=future.result()
                print(f'Case {n}: archived ({len(collected)}/{len(links)})',flush=True)
            except Exception as error:
                errors.append(dict(guiding_number=n,error=type(error).__name__,detail=str(error)[:160]))
                print(f'Case {n}: not imported ({type(error).__name__})',flush=True)
    # Keep previously checked seeds if a website page is temporarily unavailable.
    for n,d in old.items():collected.setdefault(n,d)
    docs=[collected[n] for n in sorted(collected)]
    (DATA/'cases.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
    result=dict(index_url=INDEX,index_pages=last,discovered_cases=len(links),stored_cases=len(docs),
        failed=errors,missing_guiding_numbers=sorted(set(range(1,max(links or {0:None})+1))-set(collected)),
        collected_at=datetime.now(timezone.utc).isoformat(),runtime_network_search=False,
        scope='官方公开指导案例栏目可发现的发布文本；不含登录后案例库，不代表全国裁判文书全量。')
    (DATA/'case-collection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');main(parser.parse_args().refresh)
