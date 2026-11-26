"""Download official Word text and strictly split articles, with resumable per-source results."""
import argparse,hashlib,io,json,re,zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor,as_completed
from official_bulk import ROOT,RAW,fetch,json_fetch,dump
from collect_laws_extra import cn_number

ARTICLE=re.compile(r'(?m)^[ \t\u3000]*第([零〇一二三四五六七八九十百千万]+)条(?:之([一二三四五六七八九十]+))?[ \t\u3000]*')
CHAPTER=re.compile(r'(?m)^\s*第[零一二三四五六七八九十百千]+[编章节](?:\s|　).*$',re.M)
def normalized(text):return re.sub(r'\s+','',text)
def digest(text):return hashlib.sha256(text.encode()).hexdigest()

def word_text(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist())>60_000_000:raise ValueError('Oversized source document')
        xml=ET.fromstring(z.read('word/document.xml'))
    ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    return '\n'.join(''.join(n.text or '' for n in p.iter(ns+'t')).strip() for p in xml.iter(ns+'p'))

def split_articles(text):
    matches=list(ARTICLE.finditer(text))
    if not matches:raise ValueError('No numbered articles; archived, awaiting full-document handling')
    nums=[cn_number(m[1].replace('〇','零')) for m in matches]
    labels=[str(n)+(('之'+str(cn_number(m[2]))) if m[2] else '') for n,m in zip(nums,matches)]
    if nums[0]!=1 or sorted(set(nums))!=list(range(1,max(nums)+1)) or len(labels)!=len(set(labels)) or nums!=sorted(nums):
        raise ValueError('Noncontinuous or repeated article numbers; manual review required')
    result=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        body=CHAPTER.split(text[m.start():end])[0].strip()
        if '\ufffd' in body or '???' in body or len(body)<5:raise ValueError('Damaged source text')
        result.append((labels[i],body))
    return result

def collect(item):
    key=item['bbbs'];result_path=RAW/f'npc/parsed/{key}.json'
    if result_path.exists():return json.loads(result_path.read_text(encoding='utf-8'))
    endpoint='https://flk.npc.gov.cn/law-search/search/flfgDetails?bbbs='+key
    detail,meta=json_fetch(endpoint,f'npc/details/{key}.json');d=detail['data']
    if d['bbbs']!=key or normalized(d['title'])!=normalized(item['title']):raise ValueError('Catalog/detail title mismatch')
    file_path=RAW/f'npc/word/{key}.docx'
    if file_path.exists():
        raw,file_meta=fetch('https://flk.npc.gov.cn/',f'npc/word/{key}.docx')
    else:
        download_endpoint='https://flk.npc.gov.cn/law-search/download/pc?format=docx&bbbs='+key
        download_raw,_=fetch(download_endpoint,f'npc/download/{key}.json',refresh=True)
        link=json.loads(download_raw)
        if link.get('code')!=200 or not link.get('data',{}).get('url'):raise ValueError('Official Word download unavailable')
        raw,file_meta=fetch(link['data']['url'],f'npc/word/{key}.docx')
    text=word_text(raw);parts=split_articles(text)
    title=d['title'];status={1:'已废止',2:'已修改',3:'有效',4:'尚未生效'}.get(d.get('sxx'),'未知')
    # Store source-declared status; no inference from publication dates.
    result=dict(bbbs=key,title=title,classification=d['flxz'],source_status=status,source_status_code=d.get('sxx'),
       published_at=d.get('gbrq'),effective=d.get('sxrq'),issuer=d.get('zdjgName'),url='https://flk.npc.gov.cn/detail?id='+key,
       detail_endpoint=endpoint,raw_path=file_path.relative_to(ROOT/'data').as_posix(),source_sha256=hashlib.sha256(raw).hexdigest(),
       metadata_path=f'raw/bulk/npc/details/{key}.json',metadata_sha256=meta['sha256'],retrieved_at=file_meta['retrieved_at'],
       article_count=len(parts),articles=[dict(article=n,text=t,text_sha256=digest(t)) for n,t in parts])
    dump(result_path,result);return result

def main(scope='national',limit=0,workers=3):
    catalog=json.loads((ROOT/'data/npc-catalog-all.json').read_text(encoding='utf-8'))
    items=[x for x in catalog['items'] if scope=='all' or x['flxz']!='地方法规']
    # Statutes first, then regulations, then interpretations and other records.
    order={'宪法':0,'法律':1,'行政法规':2,'监察法规':3,'司法解释':4}
    items.sort(key=lambda x:(order.get(x['flxz'],5),x['title'],x['bbbs']))
    if limit:items=items[:limit]
    failures=[];success=[]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        tasks={pool.submit(collect,item):item for item in items}
        for i,f in enumerate(as_completed(tasks),1):
            item=tasks[f]
            try:success.append(f.result())
            except Exception as e:failures.append(dict(bbbs=item['bbbs'],title=item['title'],url='https://flk.npc.gov.cn/detail?id='+item['bbbs'],error=type(e).__name__,reason=str(e)[:200]))
            if i%20==0:print(json.dumps(dict(processed=i,total=len(items),parsed=len(success),failed=len(failures))),flush=True)
    dump(ROOT/f'data/npc-text-collection-{scope}.json',dict(scope=scope,catalog_complete=catalog['complete'],target_records=len(items),parsed=len(success),articles=sum(x['article_count'] for x in success),failures=failures,source_ids=[x['bbbs'] for x in success]))
    print(json.dumps(dict(parsed=len(success),articles=sum(x['article_count'] for x in success),failed=len(failures))),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=('national','all'),default='national');p.add_argument('--limit',type=int,default=0);p.add_argument('--workers',type=int,default=3);a=p.parse_args();main(a.scope,a.limit,a.workers)
