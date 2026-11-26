"""Recover additional decisions from the already archived official court corpus."""
import json,re
from official_bulk import ROOT,dump
from parse_court_bulk import body
records=json.loads((ROOT/'data/court-collection-interpretations.json').read_text(encoding='utf-8'))['items']
existing={json.loads(p.read_text(encoding='utf-8'))['url'] for p in (ROOT/'data/raw/bulk/validity/parsed').glob('*.json')}
out=[]
for r in records:
 if r['url'] in existing or not re.search(r'关于(?:修改|废止)',r['title']) or not any(x in r['title'] for x in ('决定','通知')):continue
 try:
  text,_=body(r)
  dates=re.findall(r'自\s*((?:19|20)\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日(?:起)?施行',text[:2500])
  if not dates:out.append(dict(title=r['title'],status='无明确施行日期，待核验'));continue
  y,m,d=dates[0];effective=f'{y}-{int(m):02d}-{int(d):02d}'
  if effective>'2026-11-13':continue
  key='archived-decision-'+r['url'].rsplit('/',1)[-1].split('.')[0]
  item=dict(r,key=key,effective=effective,text=text)
  dump(ROOT/f'data/raw/bulk/validity/parsed/{key}.json',item)
  out.append(dict(title=r['title'],effective=effective,status='归档效力证据'))
 except Exception as e:out.append(dict(title=r['title'],status='待核验',reason=str(e)))
dump(ROOT/'data/validity-archived-decisions.json',out);print(json.dumps(out,ensure_ascii=False))
