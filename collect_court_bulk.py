"""Discover and archive complete public SPC interpretation/typical-case catalogs."""
import argparse,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from bs4 import BeautifulSoup
from official_bulk import ROOT,fetch,dump

COLLECTIONS={'interpretations':('fabu',16),'typical-cases':('zixun',104)}
def index_page(kind,number):
    section,code=COLLECTIONS[kind];suffix='' if number==1 else '_'+str(number)
    url=f'https://www.court.gov.cn/{section}/gengduo/{code}{suffix}.html'
    raw,meta=fetch(url,f'court/{kind}/index-{number}.html')
    soup=BeautifulSoup(raw,'html.parser');links={}
    for a in soup.select('a[href]'):
        href=a['href'];title=a.get('title') or a.get_text(' ',strip=True)
        if re.fullmatch('/'+section+r'/xiangqing/\d+\.html',href):links['https://www.court.gov.cn'+href]=title
    pages=[int(n) for n in re.findall('/'+section+f'/gengduo/{code}'+r'_(\d+)\.html',str(soup))]
    return dict(url=url,meta=meta,links=links,last=max(pages or [1]))

def main(kind):
    first=index_page(kind,1);links=dict(first['links']);failures=[];pages=[first]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(index_page,kind,n):n for n in range(2,first['last']+1)}
        for f in as_completed(tasks):
            try:p=f.result();links.update(p['links']);pages.append(p)
            except Exception as e:failures.append(dict(stage='catalog',page=tasks[f],error=type(e).__name__))
    dump(ROOT/f'data/court-catalog-{kind}.json',dict(kind=kind,index_pages=len(pages),expected_pages=first['last'],complete=len(pages)==first['last'],items=[dict(url=u,title=t) for u,t in sorted(links.items())],failures=failures))
    print(kind,'discovered',len(links),'pages',len(pages),flush=True)
    def archive(item):
        url,title=item;name=url.rsplit('/',1)[-1]
        raw,meta=fetch(url,f'court/{kind}/{name}');soup=BeautifulSoup(raw,'html.parser')
        body=soup.select_one('.txt_txt');heading=soup.select_one('.detail > .title')
        if body is None:raise ValueError('No official body')
        return dict(url=url,title=heading.get_text(' ',strip=True) if heading else title,raw_path=f'raw/bulk/court/{kind}/{name}',source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'])
    stored=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(archive,item):item[0] for item in links.items()}
        for i,f in enumerate(as_completed(tasks),1):
            try:stored.append(f.result())
            except Exception as e:failures.append(dict(stage='body',url=tasks[f],error=type(e).__name__,reason=str(e)[:160]))
            if i%25==0:print(kind,'archived',len(stored),'/',len(links),'failures',len(failures),flush=True)
    report=dict(kind=kind,discovered=len(links),archived=len(stored),items=sorted(stored,key=lambda d:d['url']),failures=failures,
       scope='Official publication pages only; archive counts are not parsed laws or cases.')
    dump(ROOT/f'data/court-collection-{kind}.json',report)
    print(kind,'complete:',len(stored),'archived;',len(failures),'failures',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('kind',choices=COLLECTIONS);main(p.parse_args().kind)
