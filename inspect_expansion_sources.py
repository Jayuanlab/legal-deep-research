"""Build-time source inspection, retaining official HTTP bytes and metadata."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from collect_laws_extra import DATA, fetch, page_text, ARTICLE, cn_number, write_json

SOURCES = {
    'labor-i': 'https://www.court.gov.cn/zixun/xiangqing/282121.html',
    'labor-ii': 'https://www.court.gov.cn/zixun/xiangqing/472691.html',
    'evidence': 'https://www.court.gov.cn/zixun/xiangqing/212721.html',
    'lending': 'https://www.court.gov.cn/zixun/xiangqing/282621.html',
    'sale': 'https://www.court.gov.cn/zixun/xiangqing/282621.html',
    'tort-i': 'https://www.court.gov.cn/zixun/xiangqing/443891.html',
    'face': 'https://www.court.gov.cn/fabu/xiangqing/315851.html',
    'family-ii': 'https://www.court.gov.cn/zixun/xiangqing/452771.html',
    'family-i': 'https://www.court.gov.cn/zixun/xiangqing/282071.html',
    'construction': 'https://www.court.gov.cn/zixun/xiangqing/282111.html',
    'time-effect': 'https://www.court.gov.cn/zixun/xiangqing/282051.html',
    'labor-cases': 'https://www.court.gov.cn/zixun/xiangqing/472681.html',
    'contract-cases': 'https://www.court.gov.cn/zixun/xiangqing/419392.html',
    'consumer-2023': 'https://www.court.gov.cn/zixun/xiangqing/393481.html',
    'consumer-2025': 'https://www.court.gov.cn/zixun/xiangqing/467931.html',
    'platform-2026': 'https://www.court.gov.cn/zixun/xiangqing/507691.html',
    'privacy-cases': 'https://www.court.gov.cn/zixun/xiangqing/499271.html',
}

def inspect(item,refresh=False):
    key,url=item
    path=DATA/'raw'/('expansion-'+key+'.html')
    if path.exists() and not refresh:
        raw=path.read_bytes(); meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    elif refresh:
        raw,meta=fetch(dict(url=url));path.write_bytes(raw);write_json(path.with_suffix('.json'),meta)
    else:
        raise FileNotFoundError('Missing archive; download only with --refresh: '+key)
    html=raw.decode(meta['encoding']);soup=BeautifulSoup(html,'html.parser')
    body=soup.select_one('.txt_txt') or soup.select_one('.txt') or soup.select_one('article')
    text=page_text(str(body) if body else html)
    text='\n'.join(x.strip() for x in text.splitlines() if x.strip())
    path.with_suffix('.txt').write_text(text,encoding='utf-8')
    nums=[cn_number(m[1]) for m in ARTICLE.finditer(text)]
    lines=text.splitlines()
    headers=[x[:180] for x in lines if re.match(r'^(?:案例|[一二三四五六七八九十]+[、.．])',x)]
    return dict(key=key,chars=len(text),articles=nums,head=text[:650],tail=text[-650:],case_headers=headers)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');args=parser.parse_args()
    def safe_inspect(item):
        try:return inspect(item,args.refresh)
        except Exception as e:return dict(key=item[0],error=str(e))
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(safe_inspect,SOURCES.items()):print(json.dumps(result,ensure_ascii=False),flush=True)
