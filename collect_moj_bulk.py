"""Archive the official administrative-regulations inventory and current linked texts."""
import json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from bs4 import BeautifulSoup
from official_bulk import ROOT,RAW,fetch,dump
from collect_laws_extra import page_text
from collect_npc_texts import split_articles,digest

BASE='https://xzfg.moj.gov.cn'
def catalog_page(n):
    url=BASE+'/search2.html'+('?PageIndex='+str(n) if n>1 else '')
    raw,meta=fetch(url,f'moj/index-{n}.html');soup=BeautifulSoup(raw,'html.parser')
    links={}
    # Only the main title in each list item, never the historical-version links.
    for node in soup.select('.list-item'):
        a=node.select_one('a[href*="/front/law/detail?LawID="]')
        if a:links[a['href']]=a.get_text(' ',strip=True)
    last=soup.select_one('#page-count');total=soup.select_one('#law-total')
    return dict(links=links,last=int(last['value']) if last else 0,total=int(total['value']) if total else 0)

def detail(item):
    url,title=item;key=re.search(r'LawID=(\d+)',url)[1]
    raw,meta=fetch(url,f'moj/details/{key}.html');soup=BeautifulSoup(raw,'html.parser')
    node=soup.select_one('.law-chapter')
    if node is None or '第一条' not in node.get_text():raise ValueError('No numbered body')
    text='\n'.join(x.strip() for x in page_text(str(node)).splitlines() if x.strip())
    parts=split_articles(text)
    head=text[:text.find('第一条')];effective=re.findall(r'自(\d{4})年(\d{1,2})月(\d{1,2})日起施行',head)
    date=None
    if effective:
        y,m,d=effective[-1];date=f'{y}-{int(m):02d}-{int(d):02d}'
    return dict(key='moj-'+key,title=title,url=url,raw_path=f'raw/bulk/moj/details/{key}.html',source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'],
        effective=date,version_note=head[:2000],articles=[dict(article=n,text=t,text_sha256=digest(t)) for n,t in parts],article_count=len(parts),classification='行政法规')

def main():
    first=catalog_page(1);links=dict(first['links']);failures=[]
    if not first['last'] or not links:raise ValueError('Unrecognized official catalog')
    with ThreadPoolExecutor(max_workers=3) as pool:
        for f in as_completed({pool.submit(catalog_page,n):n for n in range(2,first['last']+1)}):
            try:links.update(f.result()['links'])
            except Exception as e:failures.append(dict(stage='catalog',error=type(e).__name__))
    dump(ROOT/'data/moj-catalog.json',dict(expected_records=first['total'],records=len(links),complete=len(links)==first['total'],items=[dict(url=u,title=t) for u,t in links.items()],failures=failures))
    print('MOJ catalog',len(links),'expected',first['total'],flush=True)
    def collect(item):
        key=re.search(r'LawID=(\d+)',item[0])[1];p=RAW/f'moj/parsed/{key}.json'
        if p.exists():return json.loads(p.read_text(encoding='utf-8'))
        result=detail(item);dump(p,result);return result
    good=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(collect,item):item for item in links.items()}
        for i,f in enumerate(as_completed(tasks),1):
            try:good.append(f.result())
            except Exception as e:failures.append(dict(stage='body',url=tasks[f][0],title=tasks[f][1],error=type(e).__name__,reason=str(e)[:180]))
            if i%25==0:print('MOJ parsed',len(good),'/',len(links),'failures',len(failures),flush=True)
    dump(ROOT/'data/moj-collection.json',dict(target_records=len(links),parsed=len(good),articles=sum(x['article_count'] for x in good),failures=failures,source_ids=[x['key'] for x in good]))
    print('MOJ finished',len(good),'texts',sum(x['article_count'] for x in good),'articles',flush=True)

if __name__=='__main__':main()
