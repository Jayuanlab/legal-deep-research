"""Official market-regulator republications of national statutes and regulations."""
import json,math,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from urllib.parse import urlencode,urljoin
from bs4 import BeautifulSoup
from official_bulk import ROOT,RAW,fetch,dump
from collect_laws_extra import page_text
from collect_npc_texts import split_articles,digest

BASE='https://www.samr.gov.cn'
def main():
    source=BeautifulSoup(fetch(BASE+'/zw/flfg/','samr/samr.html')[0],'html.parser').select_one('script[querydata]')
    payload=json.loads(source['querydata'].replace("'",'"'))
    def page(n):
        query=dict(payload,paramJson=json.dumps(dict(pageNo=n,pageSize=20)))
        raw,_=fetch(BASE+source['url']+'?'+urlencode(query),f'samr/index-{n}.json')
        html=json.loads(raw)['data']['html'];soup=BeautifulSoup(html,'html.parser')
        return soup
    first=page(1);count=int(first.select_one('.pagination')['count']);links={}
    def add(soup):
        for a in soup.select('.nav04Left02_content a[href]'):links[urljoin(BASE,a['href'])]=a.get('title') or a.get_text(' ',strip=True)
    add(first)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for p in pool.map(page,range(2,math.ceil(count/20)+1)):add(p)
    dump(ROOT/'data/samr-catalog.json',dict(expected_records=count,records=len(links),complete=len(links)==count,items=[dict(url=u,title=t) for u,t in links.items()]))
    print('SAMR catalog',len(links),flush=True)
    def collect(item):
        url,title=item;key=url.rsplit('/',1)[-1].split('.')[0];p=RAW/f'samr/parsed/{key}.json'
        if p.exists():
            cached=json.loads(p.read_text(encoding='utf-8'))
            derived='法律' if title.startswith('中华人民共和国') and title.endswith(('法','法典')) and not title.endswith('办法') else '法规'
            if cached['classification']!=derived:cached['classification']=derived;dump(p,cached)
            return cached
        raw,meta=fetch(url,f'samr/details/{key}.html');soup=BeautifulSoup(raw,'html.parser')
        candidates=soup.select('#zoom,.TRS_Editor,.article-content,.article_content,.content-detail')
        node=next((n for n in candidates if '第一条' in n.get_text()),None)
        if node is None:
            # Reviewable fallback: full page must still pass exact consecutive numbers.
            text=page_text(str(soup))
        else:text=page_text(str(node))
        text='\n'.join(x.strip() for x in text.splitlines() if x.strip())
        text=re.split(r'\n(?:打印本页|关闭窗口|扫一扫在手机|责任编辑[：:]|相关附件|相关新闻)',text)[0].rstrip()
        parts=split_articles(text)
        # Final tail must be an actual law paragraph, not a government footer.
        if re.search(r'网站|版权所有|ICP备|主办单位|承办单位',parts[-1][1]):raise ValueError('Uncertain last-article boundary')
        first=text[:text.find('第一条')];result=dict(key=key,title=title,url=url,raw_path=f'raw/bulk/samr/details/{key}.html',source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'],
             version_note=first[-3000:],classification='法律' if title.startswith('中华人民共和国') and title.endswith(('法','法典')) and not title.endswith('办法') else '法规',article_count=len(parts),articles=[dict(article=n,text=t,text_sha256=digest(t)) for n,t in parts])
        dump(p,result);return result
    success=[];failures=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(collect,x):x for x in links.items()}
        for i,f in enumerate(as_completed(tasks),1):
            try:success.append(f.result())
            except Exception as e:failures.append(dict(url=tasks[f][0],title=tasks[f][1],error=type(e).__name__,reason=str(e)[:200]))
            if i%25==0:print('SAMR parsed',len(success),'/',len(links),'failures',len(failures),flush=True)
    dump(ROOT/'data/samr-collection.json',dict(target_records=len(links),parsed=len(success),articles=sum(x['article_count'] for x in success),failures=failures,source_ids=[x['key'] for x in success]))
    print('SAMR finished',len(success),'texts',sum(x['article_count'] for x in success),'articles',flush=True)

if __name__=='__main__':main()
