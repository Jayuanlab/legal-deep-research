"""Archive the official repeal list; match title AND issued instrument number."""
import json,re
from bs4 import BeautifulSoup
from official_bulk import ROOT,fetch,dump
from collect_laws_extra import page_text

url='https://www.sdcourt.gov.cn/jningzcfy/386500/386502/6714812/index.html'
raw,meta=fetch(url,'validity/spc-repeal-2020-16.html',timeout=25,retries=1)
soup=BeautifulSoup(raw,'html.parser')
rows=[]
for tr in soup.select('tr'):
 cells=[c.get_text('',strip=True) for c in tr.select('td')]
 if len(cells)>=3 and re.fullmatch(r'\d+',cells[0]):rows.append(cells)
dump(ROOT/'data/law-validity-repeal-source.json',dict(url=url,raw_path='raw/bulk/validity/spc-repeal-2020-16.html',source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'],effective='2021-01-01',rows=rows))
print('ROWS',len(rows));print(json.dumps(rows[:3],ensure_ascii=False));print(page_text(str(soup))[-1600:])
