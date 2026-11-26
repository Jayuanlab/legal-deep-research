"""Alternative official-source collection, with edition and full-text validation."""
import argparse,hashlib,io,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import urlparse,parse_qs,urljoin
from bs4 import BeautifulSoup
from official_bulk import ROOT,RAW,fetch,dump,allowed
from collect_laws_extra import page_text
from collect_npc_texts import ARTICLE,split_articles,normalized,digest

OUT=RAW/'gap185'
OUT.mkdir(exist_ok=True)
BAD=re.compile(r'征求意见|草案|解读|释义|答记者问|节选|起草说明')
SELECTORS='#zoom,#Zoom,#UCAP-CONTENT,#ArticleContent,.TRS_Editor,.txt_txt,.article-content,.article_content,.content-article,.content_article,.article-con,.content-text,.view.TRS_UEDITOR,.Custom_UnionStyle,.pages_content,.contxt,.xilan_con,.zwxl-content,.contentMain,.articleContent'

def canonical(t):return re.sub(r'[\s《》〈〉“”"—\-：:（）()]+','',t)
def main_title_matches(name,title):
    a=canonical(name);b=canonical(title)
    if a not in b:return False
    tail=b.split(a,1)[1]
    return not re.match(r'实施(?:条例|办法|细则|规定)|(?:司法)?解释|修正案|修正草案|草案',tail)
def read_source(url):
    name=digest(url);path=f'gap185/pages/{name}.raw'
    raw,meta=fetch(url,path,timeout=16,retries=1,origin_circuit=False)
    if raw.startswith(b'%PDF'):
        from pypdf import PdfReader
        if len(raw)>15_000_000:raise ValueError('Large PDF requires document boundary review')
        pdf=PdfReader(io.BytesIO(raw),strict=True)
        if len(pdf.pages)>100:raise ValueError('Gazette/large PDF requires document boundary review')
        text='\n'.join(p.extract_text() or '' for p in pdf.pages)
        # Remove only repeated identical page headers and numeric page numbers.
        pages=[(p.extract_text() or '').splitlines() for p in pdf.pages]
        from collections import Counter
        counts=Counter(line.strip() for page in pages for line in set(page[:2]+page[-2:]))
        repeated={s for s,n in counts.items() if n>len(pages)//2 and len(s)<100 and not ARTICLE.match(s)} if len(pages)>2 else set()
        text='\n'.join(line for page in pages for line in page if line.strip() not in repeated and not re.fullmatch(r'\s*[-—]?\s*\d{1,3}\s*[-—]?\s*',line))
        return [(text,True)],meta,path,'pdf'
    match=re.search(br'charset\s*=\s*[\"\x27]?([a-zA-Z0-9_-]+)',raw[:15000],re.I)
    encoding=match[1].decode() if match else 'utf-8'
    try:html=raw.decode(encoding)
    except UnicodeDecodeError:html=raw.decode('gb18030')
    soup=BeautifulSoup(html,'html.parser')
    title=soup.title.get_text(' ',strip=True) if soup.title else ''
    if BAD.search(title):raise ValueError('Draft/commentary/excerpt title')
    nodes=soup.select(SELECTORS)
    # Unknown government templates: use ancestors of the first article paragraph,
    # ordered by article coverage, instead of treating the entire page as law text.
    first_para=next((p for p in soup.find_all(['p','div']) if re.match(r'^\s*第\s*一\s*条',p.get_text(' ',strip=True)) and len(p.get_text())<1500),None)
    if first_para:
        ancestors=[p for p in first_para.parents if p.name in ('div','section','article','main','td')]
        nodes+=sorted(ancestors,key=lambda p:len(ARTICLE.findall(page_text(str(p)))),reverse=True)
    else:
        for h in soup.select('h1,h2,.title,.article-title'):
            if len(h.get_text(strip=True))<8:continue
            nodes.extend(p for p in h.parents if p.name in ('div','article','main','section') and 80<len(p.get_text())<18000)
    versions=[]
    for node in nodes:
        t=page_text(str(node));t='\n'.join(x.strip() for x in t.splitlines() if x.strip())
        if len(t)>50:versions.append((t,True))
    text=page_text(str(soup));text='\n'.join(x.strip() for x in text.splitlines() if x.strip())
    versions.append((text,False))
    return versions,meta,path,title

def clean_text(text):
    text=text.translate(str.maketrans('０１２３４５６７８９','0123456789'))
    text=re.sub(r'(?m)^第[ \t]*([零〇一二三四五六七八九十百千万 \t]+)条',lambda m:'第'+re.sub(r'\s+','',m[1])+'条',text)
    text=re.sub(r'(?m)^\s*\d{1,3}\s*/\s*\d{1,3}\s*$','',text)
    # Normalize PDF letter-spacing, retaining paragraphs and original HTTP bytes.
    if len(re.findall(r'[\u4e00-\u9fff] [\u4e00-\u9fff]',text))>len(text)/35:
        text=re.sub(r'(?<=[\u4e00-\u9fff])[ \t]+(?=[\u4e00-\u9fff])','',text)
    text=re.split(r'\n\s*(?:\[|【|（)?(?:相关(?:附件|链接|新闻|文章)|责任编辑[：:]|责编[：:]|扫一扫|打印本页|关闭窗口|网站地图|主办单位|版权所有|Copyright|网站标识码|京ICP备|返回首页|字体[：:])',text,flags=re.I)[0].rstrip()
    text=re.split(r'\n发布时间[：:]',text)[0]
    text=re.sub(r'\n\s*\d{1,3}\s*$','',text).rstrip()
    return text

def parse_candidate(target,url):
    versions,meta,path,page_title=read_source(url);name=target['name'];required=max(map(int,re.findall(r'(?:19|20)\d{2}',target['source_entry'])),default=0)
    source_title=page_title;rule=None
    overrides=ROOT/'data/gap185-extraction-overrides.json'
    if overrides.exists():
        rule=next((r for r in json.loads(overrides.read_text(encoding='utf-8')) if r['name']==name and r['url']==url),None)
        if rule:
            full=versions[-1][0];start=full.index(rule['start']);end=full.index(rule['end'],start)
            versions=[(full[start:end].strip(),True)]
            if rule.get('directory_title_binding'):page_title=name
    errors=[]
    for text,scoped in versions:
        try:
            text=clean_text(text)
            if scoped and canonical(name) not in canonical(text[:8000]) and main_title_matches(name,page_title):
                text=name+'\n'+text
            if canonical(name) not in canonical(text[:8000]):raise ValueError('Law title absent near document heading')
            if '\ufffd' in text or '???' in text:raise ValueError('Corrupt text')
            text=re.split(r'\n(?:相关(?:附件|链接|新闻|文章)|责任编辑[：:]|扫一扫|打印本页|关闭窗口|网站地图|主办单位|版权所有)',text)[0].rstrip()
            first=ARTICLE.search(text)
            head=text[:first.start()] if first else text[:3500]
            if first and canonical(name) not in canonical(head):raise ValueError('Expected law is not the document heading before article 1')
            if first and re.search(re.escape(canonical(name))+r'实施(?:条例|办法|细则|规定)',canonical(head[:1200])):raise ValueError('Implementing regulation cannot substitute the statute')
            edition_spans=[m[0] for m in re.finditer(r'[（(][^（）()]{0,6000}[）)]',head,re.S) if re.search('通过|修正|修订|公布',m[0])]
            version_text='\n'.join(edition_spans) or head
            years=list(map(int,re.findall(r'(?:19|20)\d{2}(?=\s*年)',version_text)))
            original_only=len(set(re.findall(r'(?:19|20)\d{2}',target['source_entry'])))==1
            if required and max(years or [0])<required and not original_only:raise ValueError(f'Edition evidence older than benchmark {required}')
            if re.search(r'草案|征求意见',head[-1200:]):raise ValueError('Draft heading')
            try:
                parts=[(None,text)] if '关于批准' in name and scoped else split_articles(text)
            except ValueError:
                if first or not scoped:raise
                if not any(w in name for w in ('决定','规定','决议','办法','条例')):raise ValueError('Expected article structure absent')
                parts=[(None,text)]
            if name.endswith('法') and parts[0][0] and re.search(r'制定本(?:规定|条例)',normalized(parts[0][1])):
                raise ValueError('Implementing text cites the law but is not the law')
            if parts[0][0] is None:
                if not main_title_matches(name,page_title):raise ValueError('Whole text heading is not the target normative document')
                remainder=normalized(text).replace(normalized(name),'')
                if len(remainder)<35 or not re.search(r'批准|通过|决定如下|作如下决定|决议如下|同意|原则|施行|规定如下',remainder):raise ValueError('No operative resolution text beyond heading')
            last=parts[-1][1]
            if first and len(parts)<3 and not any(w in name for w in ('决定','规定','决议')):raise ValueError('Too few articles; possible excerpt')
            if re.search(r'ICP备|版权所有|主办单位|技术支持|返回首页|推荐阅读|分享至|【字体|网站标识码',last):raise ValueError('Footer contamination')
            # A scoped whole-text source or a final legal closing sentence is required.
            if not scoped and not re.search(r'(施行|执行|适用|废止|公布|解释|规定|决定|批准|生效)[。；]?\s*$',last):raise ValueError('Uncertain final boundary')
            result=dict(validation_version=2,name=name,source_entry=target['source_entry'],required_year=required,edition_year=max(years or [0]),edition_evidence=version_text[-6000:],
                 url=url,raw_path='raw/bulk/'+path,source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'],page_title=page_title,scoped=scoped,
                 edition_basis='原文年份证据' if max(years or [0])>=required else '目录仅列原始公布版本；原文未注明年份，保留待核验说明',
                 article_count=sum(n is not None for n,t in parts),parts=[dict(article=n,text=t,text_sha256=digest(t)) for n,t in parts])
            if rule and rule.get('directory_title_binding'):
                result.update(page_title=source_title,title_binding=rule['directory_title_binding'],source_page_status=rule['source_page_status'],reference_status='not_reference')
            return result
        except Exception as e:errors.append(str(e))
    raise ValueError('; '.join(dict.fromkeys(errors))[:350])

def main(workers=4):
    coverage=json.loads((ROOT/'data/national-coverage.json').read_text(encoding='utf-8'))
    targets=[x for x in coverage['rows'] if not x['present']]
    # Freeze the original task list so later coverage refresh cannot shrink the job silently.
    frozen=ROOT/'data/gap185-targets.json'
    if not frozen.exists():dump(frozen,targets)
    else:targets=json.loads(frozen.read_text(encoding='utf-8'))
    batches=json.loads((ROOT/'data/gap185-search-candidates.json').read_text(encoding='utf-8'))
    priority=ROOT/'data/gap185-priority-sources.json'
    preferred=json.loads(priority.read_text(encoding='utf-8')) if priority.exists() else []
    byname={n:[r for r in preferred if r['name']==n]+[r for b in reversed(batches) if n in b['names'] for r in b['results']] for n in [t['name'] for t in targets]}
    def collect(t):
        key=digest(t['name']);cached=OUT/f'parsed/{key}.json'
        previous=json.loads(cached.read_text(encoding='utf-8')) if cached.exists() else None
        if previous and previous.get('validation_version')==2:return previous
        candidates=byname.get(t['name'],[])
        needle=canonical(t['name']).replace('中华人民共和国','')
        matching=[r for r in candidates if needle in canonical(r['title'])]
        candidates=sorted(matching or candidates,key=lambda r:(canonical(t['name']) not in canonical(r['title']),'.pdf' in r['url'].lower()))[:8]
        if previous:candidates.insert(0,dict(url=previous['url'],title=t['name']))
        failures=[];seen=set()
        for r in candidates:
            url=r['url']
            if url in seen or not allowed(url) or 'flk.npc.gov.cn' in url:continue
            seen.add(url)
            # Resolve an official PDF viewer's actual same-origin attachment.
            if 'viewer.html?' in url and 'file' in parse_qs(urlparse(url).query):url=urljoin(url,parse_qs(urlparse(url).query)['file'][0])
            try:
                result=parse_candidate(t,url);dump(cached,result);return result
            except Exception as e:failures.append(dict(url=url,error=type(e).__name__,reason=str(e)[:350]))
        dump(OUT/f'failed/{key}.json',dict(name=t['name'],attempts=failures))
        return dict(name=t['name'],failed=True,attempts=len(failures))
    good=[];bad=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks=[pool.submit(collect,t) for t in targets]
        for i,f in enumerate(as_completed(tasks),1):
            r=f.result()
            (bad if r.get('failed') else good).append(r)
            if i%10==0:print(json.dumps(dict(processed=i,targets=len(targets),success=len(good),failed=len(bad))),flush=True)
    dump(ROOT/'data/gap185-collection.json',dict(targets=len(targets),success=len(good),failed=len(bad),missing=[x['name'] for x in bad],items=[dict(name=x['name'],url=x['url'],articles=x['article_count'],edition_year=x['edition_year']) for x in good]))
    print('FINISHED',len(good),'/',len(targets),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);a=p.parse_args();main(a.workers)
