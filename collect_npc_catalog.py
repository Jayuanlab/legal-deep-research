"""Collect the current public national database inventory, with pagination checks."""
import argparse,json,math
from concurrent.futures import ThreadPoolExecutor,as_completed
from official_bulk import ROOT,json_fetch,dump

URL='https://flk.npc.gov.cn/law-search/search/list'
def page(number,codes=None,statuses=None):
    payload=dict(searchRange=1,sxrq=[],gbrq=[],searchType=1,sxx=statuses or [3,4],gbrqYear=[],flfgCodeId=codes or [],zdjgCodeId=[],searchContent='',pageNum=number,pageSize=100)
    label='-'.join(map(str,codes or ['all']))
    return json_fetch(URL,f'npc/catalog-{label}-{number}.json',payload)[0]

def main(scope='all',offline=False):
    if offline:
        from official_bulk import RAW
        enum=json.loads((RAW/'npc/enum.json').read_text(encoding='utf-8'))
    else:enum,_=json_fetch('https://flk.npc.gov.cn/law-search/search/enumData','npc/enum.json')
    tree=enum['data']['flfgfl']['children']
    national=[n for n in tree if n['name']!='地方法规']
    codes=sorted({c for n in national for c in n['codeIdList'] if c}) if scope=='national' else []
    if offline:
        from official_bulk import RAW
        raw_files=sorted((RAW/'npc').glob('catalog-all-*.json'))
        raw_files=[p for p in raw_files if not p.name.endswith('.meta.json')]
        snapshots=[json.loads(p.read_text(encoding='utf-8')) for p in raw_files]
        unique={r['bbbs']:r for s in snapshots for r in s['rows']}
        dump(ROOT/'data/npc-catalog-all.json',dict(scope='all',url='https://flk.npc.gov.cn/',expected_records=snapshots[0]['total'],records=len(unique),complete=False,pages=len(snapshots),failures=[dict(error='HTTP 307 self-redirect after available pages; collection stopped rather than repeatedly retrying')],classification=tree,items=list(unique.values()),scope_note='Partial public catalog; not full-text coverage.'))
        print('Recovered partial catalog:',len(unique),'records',flush=True);return
    first=page(1,codes);total=first['total'];pages=math.ceil(total/100);rows=list(first['rows']);failures=[]
    def get(n):return n,page(n,codes)
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks={pool.submit(get,n):n for n in range(2,pages+1)}
        for f in as_completed(tasks):
            try:
                n,p=f.result();rows.extend(p['rows'])
                if len(p['rows'])!=min(100,total-(n-1)*100):failures.append(dict(page=n,error='Unexpected row count'))
                if n%10==0:print(f'Catalog {scope} page {n}/{pages}',flush=True)
            except Exception as e:failures.append(dict(page=tasks[f],error=type(e).__name__))
    unique={r['bbbs']:r for r in rows}
    result=dict(scope=scope,url='https://flk.npc.gov.cn/',expected_records=total,records=len(unique),complete=len(unique)==total and not failures,pages=pages,failures=failures,classification=tree,items=sorted(unique.values(),key=lambda r:(r['flxz'],r['title'],r['gbrq'])),
        scope_note='公开目录标为有效或尚未生效的记录；仅代表本目录快照，不代表全部中国规范或已经下载全文。')
    dump(ROOT/f'data/npc-catalog-{scope}.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('items','classification')},ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=('all','national'),default='all');p.add_argument('--offline',action='store_true');a=p.parse_args();main(a.scope,a.offline)
