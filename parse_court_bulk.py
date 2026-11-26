"""Conservative offline parsing; reject uncertain layouts, retain per-page reasons."""
import hashlib,json,re
from bs4 import BeautifulSoup
from official_bulk import ROOT,dump
from collect_laws_extra import page_text,cn_number
from collect_npc_texts import split_articles,normalized,digest

DATA=ROOT/'data'
HEAD=re.compile(r'(?m)^案例\s*([一二三四五六七八九十百0-9]+)\s*$')
INLINE=re.compile(r'(?m)^案例\s*([一二三四五六七八九十百0-9]+)[：:、.．\s][^\n]+$')
NUMBERED=re.compile(r'(?m)^([一二三四五六七八九十百]+)[、．.][^\n]+$')
SECTION=re.compile(r'【([^】]+)】|(?m:^\s*(?:[（(]?[一二三四五六七八九十]+[）)、．.])?(基本案情|简要案情|基本情况|案情简介|裁判结果|裁判理由|判决理由|典型意义|裁判要旨|裁判要点|裁判情况|相关法条)\s*$)')

def body(record):
    raw=(DATA/record['raw_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=record['source_sha256']:raise ValueError('Source hash mismatch')
    soup=BeautifulSoup(raw.decode('utf-8'),'html.parser');node=soup.select_one('.txt_txt')
    if node is None:raise ValueError('Missing official body')
    text='\n'.join(x.strip() for x in page_text(str(node)).splitlines() if x.strip())
    text=re.sub(r'[ \t\u3000]{2,}(?=案例[一二三四五六七八九十百0-9]+\s*\n)','\n',text)
    if '\ufffd' in text or '???' in text:raise ValueError('Corrupt source')
    date=re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})',page_text(str(soup)))
    return text,date[1] if date else None

def sections(text):
    matches=list(SECTION.finditer(text));parts={}
    for i,m in enumerate(matches):
        label=(m[1] or m[2]).strip();value=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
        if label in parts:raise ValueError('Repeated section label')
        parts[label]=value
    return parts

def case_parts(text):
    matches=list(HEAD.finditer(text))
    if not matches:matches=list(INLINE.finditer(text))
    if not matches:
        matches=[m for m in NUMBERED.finditer(text) if '案' in m[0] and not re.search(r'基本案情|典型意义|裁判情况|裁判结果|案情简介',m[0])]
    if not matches:raise ValueError('No reliable case boundaries')
    nums=[int(m[1]) if m[1].isdigit() else cn_number(m[1]) for m in matches]
    starts=[i for i,n in enumerate(nums) if n==1]
    if not starts:raise ValueError('No first case')
    start=starts[-1];matches=matches[start:];nums=nums[start:]
    if nums!=list(range(1,len(nums)+1)):raise ValueError('Noncontinuous case numbering')
    result=[]
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        segment=text[m.start():end].strip()
        segment=re.split(r'\n(?:相关新闻|相关链接|责任编辑[：:])',segment)[0].rstrip()
        parts=sections(segment)
        facts=parts.get('基本案情') or parts.get('简要案情') or parts.get('基本情况') or parts.get('案情简介') or parts.get('具体内容')
        reasoning=parts.get('裁判理由') or parts.get('判决理由')
        holding=parts.get('裁判结果') or parts.get('裁判情况') or parts.get('处理结果') or parts.get('执行结果')
        if len(segment)<180 or not facts or not (holding or reasoning or ('法院' in facts and re.search('判决|裁定|调解',facts))):raise ValueError('Incomplete case section '+str(i+1))
        first_section=SECTION.search(segment)
        title=segment[:first_section.start()].replace('\n',' ').strip()
        if len(title)<6 or len(title)>400:raise ValueError('Uncertain case title')
        result.append(dict(number=i+1,title=title,text=segment,source_start=m.start(),source_end=m.start()+len(segment),sections=parts,
           facts=facts,holding=holding,reasoning=reasoning,points=parts.get('裁判要点') or parts.get('裁判要旨') or parts.get('典型意义')))
    return result

def existing():
    docs=[]
    for name in ('laws.json','laws-extra.json','laws-expansion.json','cases.json','cases-extra.json'):
        docs+=json.loads((DATA/name).read_text(encoding='utf-8'))
    return docs

def main():
    old=existing();known_laws={digest(normalized(d['text'])) for d in old if d['doc_type']=='law'}
    known_cases={digest(normalized(d.get('facts') or (d.get('sections') or {}).get('具体内容') or d['text'])) for d in old if d['doc_type']=='case'}
    law_keys={(d.get('law_name'),d.get('version'),d.get('article')):d for d in old if d['doc_type']=='law'}
    laws=[];cases=[];accepted=[];rejected=[];duplicates=[];conflicts=[]
    for kind in ('interpretations','typical-cases'):
        collection=json.loads((DATA/f'court-collection-{kind}.json').read_text(encoding='utf-8'))
        for record in collection['items']:
            try:
                text,pub=body(record);sourcekey=record['url'].rsplit('/',1)[-1].split('.')[0]
                common=dict(url=record['url'],raw_path=record['raw_path'],source_sha256=record['source_sha256'],retrieved_at=record['retrieved_at'])
                if kind=='interpretations':
                    if re.search('征求意见|解读|答记者问',record['title']):raise ValueError('Draft or commentary')
                    if '修改' in record['title'] or '废止' in record['title']:raise ValueError('Amendment/repeal decision requires version-aware parsing')
                    clean=re.split(r'\n(?:相关新闻|相关链接[：:]?|责任编辑[：:])',text)[0].rstrip()
                    parts=split_articles(clean)
                    # A complete numbered text must include a closing legal rule,
                    # not end in a news link or publisher's contact section.
                    if len(parts)<2 or not re.search(r'本(?:解释|规定|批复).*?(?:施行|适用|执行)|自.*?施行',parts[-1][1],re.S):raise ValueError('Unverified final article boundary')
                    name=record['title'].replace('最高法发布','').replace('最高人民法院发布','').strip('《》')
                    version=re.search(r'法释[〔\[]\s*\d{4}\s*[〕\]]\s*\d+\s*号',text[:10000])
                    version=version[0] if version else '官方发布版本（具体文号待核验）'
                    dates=re.findall(r'本(?:解释|规定|批复)自(\d{4})年(\d{1,2})月(\d{1,2})日起施行',text)
                    effective=f'{dates[-1][0]}-{int(dates[-1][1]):02d}-{int(dates[-1][2]):02d}' if dates else None
                    imported=0
                    for number,segment in parts:
                        h=digest(normalized(segment))
                        if h in known_laws:continue
                        legal_key=(name,version,number)
                        if legal_key in law_keys:
                            conflicts.append(dict(url=record['url'],article=number,existing_id=law_keys[legal_key]['id'],reason='Same legal-version article differs in normalized text; retained archive for boundary review, not imported'))
                            continue
                        known_laws.add(h);imported+=1
                        label=('第'+number+'条') if '之' not in number else re.match(r'^第[零〇一二三四五六七八九十百千万]+条之[一二三四五六七八九十]+',segment.lstrip())[0]
                        laws.append(dict(common,id='J'+sourcekey+'A'+number.replace('之','Z'),doc_type='law',kind='司法解释官方发布原文',law_name=name,article=number,title=name+' '+label,text=segment,text_sha256=digest(segment),tags=name,topic='司法解释',version=version,date=effective,published_at=None,page_published_at=pub,
                            authority_status='最高法院来源发布版本，未完成现行效力清理；可能有后续修订或废止，须核对版本和案件发生时间',historical_law_note='不得仅因官方原文已入库而认定为现行有效；历史案件及后续修改另行核验。'))
                        law_keys[legal_key]=laws[-1]
                else:
                    parts=case_parts(text);imported=0
                    for row in parts:
                        identity=digest(normalized(row['facts']))
                        if identity in known_cases:continue
                        known_cases.add(identity);imported+=1
                        number=row.pop('number');segment=row['text']
                        cases.append(dict(common,**row,id='CT'+sourcekey+'N'+str(number),doc_type='case',kind='最高人民法院典型案例发布原文（非指导案例、非判决全文）',source_collection='spc-typical-'+sourcekey,collection_number=number,date=pub,tags=record['title'],topic='官方典型案例',text_sha256=digest(segment),case_number=None,court=None,
                            authority_status='官方典型案例发布文本；不是指导案例，未核验当前个案适用',historical_law_note='裁判适用法可能为历史版本；仅以原文可核实事实为依据，不将典型案例等同现行法条或指导案例。'))
                accepted.append(dict(url=record['url'],kind=kind,parsed=len(parts),imported=imported))
                if not imported:duplicates.append(record['url'])
            except Exception as e:rejected.append(dict(url=record['url'],title=record['title'],kind=kind,error=type(e).__name__,reason=str(e)[:200]))
    dump(DATA/'laws-judicial-bulk.json',laws);dump(DATA/'cases-bulk.json',cases)
    dump(DATA/'court-parsing-report.json',dict(laws=len(laws),cases=len(cases),accepted=accepted,rejected=rejected,duplicate_pages=duplicates,article_conflicts=conflicts,scope='Only layouts passing conservative structural checks were imported; archives include unparsed pages.'))
    from collections import Counter
    print(json.dumps(dict(laws=len(laws),cases=len(cases),accepted_pages=len(accepted),rejected_pages=len(rejected),reasons=dict(Counter(x['reason'] for x in rejected))),ensure_ascii=False),flush=True)

if __name__=='__main__':main()
