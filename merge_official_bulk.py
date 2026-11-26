"""Build additive corpus files, preserving all existing source IDs and text."""
import hashlib,json,re
from datetime import datetime
from collections import Counter
from bs4 import BeautifulSoup
from official_bulk import ROOT,RAW,dump
from collect_npc_texts import digest,normalized
from collect_laws_extra import page_text

DATA=ROOT/'data'
BASE_FILES=('laws.json','laws-extra.json','laws-expansion.json','cases.json','cases-extra.json')
def load(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    baseline=[d for n in BASE_FILES for d in load(DATA/n)]
    guiding=DATA/'cases-guiding-extra.json'
    if guiding.exists():baseline+=load(guiding)
    court_laws=load(DATA/'laws-judicial-bulk.json');court_cases=load(DATA/'cases-bulk.json')
    known={digest(normalized(d['text'])) for d in baseline+court_laws if d['doc_type']=='law'}
    # Explicit publication/effective dates from the same official catalog item.
    moj_meta={}
    for p in (RAW/'moj').glob('index-*.html'):
        soup=BeautifulSoup(p.read_bytes(),'html.parser')
        for li in soup.select('.list-item'):
            a=li.select_one('.title a[href]')
            if not a:continue
            def date(selector):
                n=li.select_one(selector);m=re.search(r'\d{4}-\d{2}-\d{2}',n.get_text()) if n else None
                return m[0] if m else None
            moj_meta[a['href']]=dict(published=date('.publish-date'),effective=date('.implemented-date'),catalog_raw=p.relative_to(DATA).as_posix())
    outputs={'laws-regulations.json':[],'laws-national.json':[]};sources=[];duplicates=0;whole=0
    inputs=[]
    for p in sorted((RAW/'moj/parsed').glob('*.json')):inputs.append(('moj',load(p)))
    # Retain the complete official body for normative texts without numbered articles.
    for failure in load(DATA/'moj-collection.json')['failures']:
        if failure.get('stage')!='body':continue
        key=re.search(r'LawID=(\d+)',failure['url'])[1];path=RAW/f'moj/details/{key}.html'
        soup=BeautifulSoup(path.read_bytes(),'html.parser');node=soup.select_one('.law-chapter')
        if node is None:raise ValueError('Missing complete source body')
        text='\n'.join(x.strip() for x in page_text(str(node)).splitlines() if x.strip())
        if len(text)<80 or '\ufffd' in text:raise ValueError('Invalid whole-text source')
        meta=load(path.with_suffix('.html.meta.json'))
        inputs.append(('moj',dict(key='moj-'+key,title=failure['title'],url=failure['url'],raw_path=path.relative_to(DATA).as_posix(),source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'],classification='行政法规库规范文本',version_note=text[:text.find('\n第一条')] if '\n第一条' in text else '',article_count=0,articles=[dict(article=None,text=text,text_sha256=digest(text))],unsegmented_reason=failure['reason'])))
    for p in sorted((RAW/'samr/parsed').glob('*.json')):inputs.append(('samr',load(p)))
    for publisher,s in inputs:
        path=DATA/s['raw_path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=s['source_sha256']:raise ValueError('Source drift')
        dates=moj_meta.get(s['url'],{})
        published=dates.get('published');effective=dates.get('effective')
        if publisher=='samr':
            future=re.findall(r'本(?:法|条例|规定|办法)自(\d{4})年(\d{1,2})月(\d{1,2})日起施行',s['articles'][-1]['text'])
            if future:
                y,m,d=future[-1];candidate=f'{y}-{int(m):02d}-{int(d):02d}'
                if candidate>datetime.now().strftime('%Y-%m-%d'):effective=candidate
        version=('司法部目录公布日期 '+published) if published else ('官网刊载版本；源哈希 '+s['source_sha256'][:12]+'；沿革见来源说明')
        statute_title=s['title'].startswith('中华人民共和国') and s['title'].endswith(('法','法典')) and not s['title'].endswith('办法')
        topic='行政法规' if publisher=='moj' else ('全国性法律' if statute_title else '全国性法规')
        imported=0;ids=[]
        for part in s['articles']:
            h=digest(normalized(part['text']))
            if h in known:duplicates+=1;continue
            known.add(h);imported+=1
            article=part['article'];key=('R' if publisher=='moj' else 'L')+digest(s['url'])[:20]+'A'+(article.replace('之','Z') if article else 'ALL')
            kind=('行政法规官方原文' if publisher=='moj' else '法律法规官方刊载原文') if article else '行政法规库规范原文（全文未分条）'
            if not article:whole+=1
            label=('第'+article+'条') if article else None
            if article and '之' in article:label=re.match(r'^第[零〇一二三四五六七八九十百千万]+条之[一二三四五六七八九十]+',part['text'].lstrip())[0]
            d=dict(id=key,doc_type='law',kind=kind,law_name=s['title'],article=article,title=s['title']+(' '+label if article else '（全文）'),
               text=part['text'],text_sha256=part['text_sha256'],url=s['url'],raw_path=s['raw_path'],source_sha256=s['source_sha256'],retrieved_at=s['retrieved_at'],
               tags=s['title'],topic=topic,version=version,date=effective,published_at=published,version_note=s.get('version_note',''),
               authority_status='官方来源发布版本；具体适用须核对施行日期、后续修订和地域范围',historical_law_note='未完成全部修订沿革与失效清理；不能将本库收录视为现行效力确认。',
               source_collection=publisher+'-national',unsegmented_reason=s.get('unsegmented_reason'))
            if effective and effective>datetime.now().strftime('%Y-%m-%d'):
                d.update(reference_status='not_reference',authority_status='目录明示尚未施行，自'+effective+'起施行；保留浏览，默认不参与研究检索。')
            outputs['laws-regulations.json' if publisher=='moj' else 'laws-national.json'].append(d);ids.append(key)
        sources.append(dict(publisher=publisher,key=s['key'],title=s['title'],url=s['url'],raw_path=s['raw_path'],source_sha256=s['source_sha256'],raw_articles=s['article_count'],imported=imported,ids=ids,dates=dates))
    for name,docs in outputs.items():dump(DATA/name,docs)
    after=baseline+court_laws+court_cases+[d for rows in outputs.values() for d in rows]
    ids=[d['id'] for d in after];assert len(ids)==len(set(ids))
    counter=Counter(d['doc_type'] for d in after)
    report=dict(before=dict(laws=2782,cases=319,total=3101),after=dict(laws=counter['law'],cases=counter['case'],total=len(after)),
       new_law_items=counter['law']-2782,new_cases=counter['case']-319,whole_text_items=whole,duplicate_articles_skipped=duplicates,
       future_law_items_excluded=sum(d.get('reference_status')=='not_reference' for d in after if d['doc_type']=='law'),sources=sources,
       scope='法条条目与未分条规范全文分别记录；目录与原文归档不等于已入研究库或全中国规范覆盖。')
    dump(DATA/'bulk-import-manifest.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='sources'},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
