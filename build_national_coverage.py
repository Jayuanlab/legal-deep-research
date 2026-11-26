"""Source-named coverage and a concrete backlog, never an inferred all-China percentage."""
import json,re,hashlib
from collections import Counter
from bs4 import BeautifulSoup
from official_bulk import ROOT,RAW,dump

DATA=ROOT/'data'
def key(name):return re.sub(r'\s+','',re.split(r'[（(]',name)[0]).strip('《》')
def main():
    source=RAW/'samr/law-list.html';soup=BeautifulSoup(source.read_bytes(),'html.parser')
    entries=[]
    for p in soup.select('p'):
        text=p.get_text('',strip=True)
        m=re.match(r'^\d+[．.、]\s*(.+)',text)
        if m:entries.append(dict(name=key(m[1]),source_entry=m[1]))
    if any('中华人民共和国宪法' in p.get_text() for p in soup.select('p')):
        entries.insert(0,dict(name='中华人民共和国宪法',source_entry='中华人民共和国宪法（版本沿革详见原目录）'))
    entries=list({x['name']:x for x in entries}.values())
    docs=[]
    for name in ('laws.json','laws-extra.json','laws-expansion.json','laws-regulations.json','laws-national.json','laws-judicial-bulk.json','laws-gap185.json'):
        docs+=json.loads((DATA/name).read_text(encoding='utf-8'))
    names=Counter(key(d['law_name']) for d in docs)
    rows=[dict(x,stored_items=names[x['name']],present=bool(names[x['name']]),status='存在来源发布版本，尚未逐一核验是否与目录版本相同' if names[x['name']] else '缺少可检索原文') for x in entries]
    missing=[x['name'] for x in rows if not x['present']]
    npc=json.loads((DATA/'npc-catalog-all.json').read_text(encoding='utf-8'))
    report=dict(benchmark='现行有效法律目录（303件），截至2026-08-28；不是2026-11-12全中国规范全集',benchmark_url='https://www.samr.gov.cn/fgs/sjdt/art/2026/art_93a4fbac2ce14ab6baab60b0cd452ef4.html',benchmark_raw=source.relative_to(DATA).as_posix(),benchmark_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        expected_names=303,parsed_names=len(entries),title_matches=sum(x['present'] for x in rows),missing_names=missing,rows=rows,
        npc_catalog=dict(expected_records=npc['expected_records'],stored_catalog_records=npc['records'],complete=npc['complete'],full_texts=0,blocker='公开API后续目录/文本请求循环重定向；尚未取得全量全文'),
        remaining_scopes=['缺失全国性法律及同名规范的版本核验','地方性法规、自治条例、单行条例、经济特区法规原文','国务院部门规章、地方政府规章','修改废止决定、历史版本、时间效力关联','香港、澳门、台湾地区规范与相应法域的独立适用建模','公开法院案例中未能可靠分案的资料；公开裁判文书与案例库登录资源'],
        claim='不得宣称覆盖所有中国法条。标题命中不代表版本一致或法条完整。')
    dump(DATA/'national-coverage.json',report)
    print(json.dumps(dict(parsed_names=len(entries),title_matches=report['title_matches'],missing=len(missing),missing_sample=missing[:20]),ensure_ascii=False))

if __name__=='__main__':main()
