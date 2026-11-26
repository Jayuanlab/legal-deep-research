"""Audit every stored source-version against archived operative evidence."""
import json,re,hashlib
from collections import defaultdict,Counter
from pathlib import Path
from bs4 import BeautifulSoup
import corpus
from official_bulk import dump
from law_validity import load_rules,LABELS,instrument
from validity_evidence import titles,canonical,amended_sections,edition_years,repeal_targets
from collect_laws_extra import page_text,cn_number
ROOT=Path(__file__).parent;AS_OF='2026-11-13'

def main():
 with corpus.connection() as db:docs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM documents WHERE doc_type='law'")]
 groups=defaultdict(list)
 for d in docs:groups[(d['law_name'],d.get('version'),d['url'])].append(d)
 byname=defaultdict(list)
 for key,ds in groups.items():byname[canonical(key[0])].append((key,ds))
 old_rules=load_rules();rules=dict(old_rules);events=[];pending=[];sources=[]
 for p in sorted((corpus.DATA/'raw/bulk/validity/parsed').glob('*.json')):
  r=json.loads(p.read_text(encoding='utf-8'))
  assert hashlib.sha256((corpus.DATA/r['raw_path']).read_bytes()).hexdigest()==r['source_sha256']
  if r['effective']<=AS_OF:sources.append(r)
 def header(d):
  text=d.get('version_note') or ''
  p=corpus.DATA/(d.get('raw_path') or '_absent')
  if p.exists() and p.suffix!='.pdf':
   raw=p.read_bytes()
   if not raw.startswith(b'%PDF'):
    try:
     soup=BeautifulSoup(raw.decode('utf-8'),'html.parser')
     node=soup.select_one('.law-chapter,.txt_txt,.TRS_Editor,#ArticleContent')
     if node:
      body=page_text(str(node));text+='\n'+re.split(r'第\s*一\s*条',body,maxsplit=1)[0][:7000]
    except UnicodeDecodeError:pass
  return text
 headers={}
 def gethead(d):
  if d['url'] not in headers:headers[d['url']]=header(d)
  return headers[d['url']]
 def status(d,code,source,quote,reason,scope='该发布版本全部条文',replacement=None):
  # Confirmed repeal outranks an earlier amendment; future records stay future.
  previous=rules.get(d['id'],{})
  if previous.get('code')=='not_yet_effective':return
  if previous.get('code')=='repealed' and code!='repealed':return
  if previous.get('code')=='partially_repealed' and code=='superseded':return
  if previous.get('effective_from','')>source['effective'] and previous.get('code')==code:return
  r=dict(code=code,label=LABELS[code],checked_at=AS_OF,effective_from=source['effective'],source_url=source['url'],raw_path=source['raw_path'],source_sha256=source['source_sha256'],evidence_quote=quote,reason=reason,scope=scope,
   document_source_sha256=d.get('source_sha256'),document_text_sha256=d.get('text_sha256'),document_version=d.get('version'))
  if replacement:r['replacement_name']=replacement
  rules[d['id']]=r
 # Explicit whole-version repeals in official annexes.
 for s in sources:
  if s['key'].startswith('repeal-') or ('废止' in s['title'] and '决定' in s['title']):
   raw=(corpus.DATA/s['raw_path']).read_bytes();soup=BeautifulSoup(raw,'html.parser')
   rows=[[c.get_text('',strip=True) for c in tr.select('td')] for tr in soup.select('tr')]
   count=0
   for row in rows:
    if len(row)<3 or not re.fullmatch(r'\d+',row[0]):continue
    count+=1
    for key,ds in byname.get(canonical(row[1]),[]):
     for d in ds:
      if instrument(row[2]) and instrument(d.get('version',''))==instrument(row[2]):status(d,'repealed',s,' | '.join(row),'规范名称与文号同时匹配官方废止目录；历史案件另行核对时间适用。')
   events.append(dict(source=s['key'],kind='repeal_annex',parsed_rows=count))
   if not count:pending.append(dict(source=s['key'],reason='网页正文未提供可可靠解析的废止目录，未据此批量标记'))
  if s['key'].startswith('regulations-'):
   parts=re.split(r'国务院决定废止的行政法规',s['text'])
   if len(parts)>1:
    for line in parts[-1].splitlines():
     m=re.match(r'^[一二三四五六七八九十百]+、\s*(.+?)[（(]',line)
     if not m:continue
     for key,ds in byname.get(canonical(m[1]),[]):
      for d in ds:status(d,'repealed',s,line,'完整规范名称匹配国务院决定所附废止目录；未将同名引用或实施细则误作本法。')
 # All stored articles and additional primary sources are scanned for explicit clauses.
 clause_sources=[]
 for key,ds in groups.items():
  for d in ds:
   if '同时废止' in d['text'] and d.get('date') and d['date']<=AS_OF:
    clause_sources.append(dict(key=d['id'],url=d['url'],raw_path=d.get('raw_path'),source_sha256=d.get('source_sha256'),effective=d['date'],text=d['text']))
 clause_sources += [s for s in sources if s['key']=='ecological-code-2026']
 for s in clause_sources:
  for sentence in re.split(r'。',s['text']):
   for target in repeal_targets(sentence):
    for key,ds in byname.get(canonical(target['name']),[]):
     issue=instrument(sentence[target['end']:]);sc=target['scope']
     partial=re.search(r'第([一二三四五六七八九十百千万]+)条',sc)
     if not partial and re.search(r'第[一二三四五六七八九十百千万]+[条款]',sc):continue
     for d in ds:
      if issue and instrument(d.get('version',''))!=issue:continue
      # Same-name replacement is not proof that its current edition is repealed.
      if not issue and canonical(key[0])==canonical(next((x['law_name'] for x in docs if x['id']==s['key']),'')):continue
      if partial:
       if str(d.get('article'))!=str(cn_number(partial[1])):continue
       code='partially_repealed';scope='仅本条第一款' if '第一款' in sc else '本条，具体范围见逐字依据'
      else:code='repealed';scope='该发布版本全部条文'
      status(d,code,s,sentence,'新规范的施行条款明确规定旧规范或指定条款废止；按完整名称、文号及条款范围匹配。',scope)
 # Amendment decisions: only editions proven older than the decision are marked.
 for s in sources:
  if not (s['key'].startswith('amend-') or s['key'].startswith('regulations-') or s['key'].startswith('archived-decision-')):continue
  sections=amended_sections(s['text'])
  if '关于修改' in s['title'] and not s['key'].startswith('regulations-'):
   title_targets=titles(s['title'])
   if len(title_targets)==1 and '等' not in s['title'].split('》')[-1]:
    sections=[dict(name=title_targets[0][0],quote=s['text'][:9000])]
  events.append(dict(source=s['key'],kind='amendment_sections',parsed_sections=len(sections)))
  # A 2020 decision taking effect in 2021 does not make its 2020 consolidated
  # republication an old edition. Compare against the decision year, not 2021.
  decision_year=min(map(int,re.findall(r'(20\d{2})年',s['text'][:500])),default=int(s['effective'][:4]))
  for sec in sections:
   for key,ds in byname.get(canonical(sec['name']),[]):
    head=gethead(ds[0]);years=edition_years(head);issue=instrument(ds[0].get('version',''))
    if issue:years.append(int(issue[0]))
    if ds[0].get('published_at'):years.append(int(ds[0]['published_at'][:4]))
    dates=re.findall(r'((?:19|20)\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日[^\n。]{0,180}?(?:通过|修订|修正|公布|发布)',head)
    latest_date=max((f'{y}-{int(m):02d}-{int(day):02d}' for y,m,day in dates),default='')
    if latest_date>=s['effective'] or (years and max(years)>=decision_year):continue
    # Explicit old edition is required. Publication URL dates alone are ignored.
    if not years:
     pending.append(dict(name=key[0],version=key[1],source=s['key'],reason='找到修改决定，但缺少原版本年份证据，保留待核验'));continue
    for d in ds:
     code='superseded';scope='修改前的历史发布版本；未宣称整部规范废止'
     # Specific deleted clauses receive a partial-repeal label within the old version.
     if d.get('article'):
      for line in sec['quote'].splitlines():
       if re.match(r'^\s*(?:\d+[.．、])?\s*(?:删去|删除)',line):
        deleted={cn_number(n) for n in re.findall(r'第([一二三四五六七八九十百千万]+)条',line)}
        for a,b in re.findall(r'第([一二三四五六七八九十百千万]+)条至第([一二三四五六七八九十百千万]+)条',line):deleted.update(range(cn_number(a),cn_number(b)+1))
        if int(d['article'].split('之')[0]) in deleted:code='partially_repealed';scope='旧版本本条所列删除范围：'+line[:400]
     status(d,code,s,sec['quote'],'官方修改决定明确修改本规范；本库存档版本的通过、修正或文号年份早于决定，尚未证明包含本次修改。',scope)
 # Every source/version receives an explicit audit outcome, including unresolved ones.
 audit=[]
 for key,ds in groups.items():
  counts=Counter(rules.get(d['id'],{}).get('code','unknown') for d in ds)
  audit.append(dict(name=key[0],version=key[1],url=key[2],records=len(ds),status_counts=dict(counts),outcome='有明确效力依据' if any(k!='unknown' for k in counts) else '未找到足够明确的版本级依据，保留待核验',checked_at=AS_OF))
 result=dict(as_of=AS_OF,scanned_records=len(docs),scanned_source_versions=len(groups),scanned_names=len(byname),source_events=events,pending_matches=pending,by_id=rules,audit=audit,scope='全库逐版本扫描并与已归档官方决定比对；待核验不表示有效，也不表示每份规范均已穷尽官网查询。')
 dump(corpus.DATA/'validity-all-proposal.json',result)
 print(json.dumps(dict(versions=len(groups),records=len(docs),counts=dict(Counter(rules.get(d['id'],{}).get('code','unknown') for d in docs)),pending=len(pending),events=events),ensure_ascii=False))
 for row in audit:
  if any(k in row['status_counts'] for k in ('superseded','partially_repealed')):print(json.dumps(row,ensure_ascii=False))
if __name__=='__main__':main()
