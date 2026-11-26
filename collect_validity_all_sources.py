import json,re
from concurrent.futures import ThreadPoolExecutor
from official_bulk import ROOT,fetch,dump
from collect_gap185 import read_source,clean_text,digest

SOURCES=[
 ('amend-laws-15-2026','https://legalinfo.moj.gov.cn/pub/sfbzhfx/zhfxfzzx/fzzxyw/202611/t20261108_541570.html','2026-11-06'),
 ('amend-environment-9-2026','https://www.court.gov.cn/fabu/xiangqing/508041.html','2026-08-15'),
 ('amend-environment-2-2026','https://www.court.gov.cn/zixun/xiangqing/508011.html','2026-08-15'),
 ('ecological-code-2026','https://legalinfo.moj.gov.cn/pub/sfbzhfx/zt/2026zt0106/xxxcsthjfd20260817/sthjfd20260817/202608/t20260818_538611.html','2026-08-15'),
 ('regulations-2022','https://app.www.gov.cn/govdata/gov/202204/07/483696/article.html','2022-05-01'),
 ('repeal-13','https://www.court.gov.cn/zixun/xiangqing/171602.html','2019-07-20'),
 ('regulations-2026-jan','https://www.beijing.gov.cn/zhengce/zhengcefagui/qtwj/202603/t20260318_4560867.html','2026-03-20'),
 ('regulations-2026-aug','https://sft.xinjiang.gov.cn/xjsft/flfggz/202608/df61a06d37774cd3a06c32ed374bde4b.shtml','2026-08-15'),
 ('amend-execution-18','https://www.court.gov.cn/fabu/xiangqing/282661.html','2021-01-01'),
 ('repeal-11','https://www.court.gov.cn/zixun/xiangqing/13243.html','2015-01-19'),
 ('repeal-12','https://www.court.gov.cn/zixun/xiangqing/61462.html','2017-10-01'),
 ('amend-civil-27','https://www.court.gov.cn/zixun/xiangqing/282621.html','2021-01-01'),
 ('amend-commercial-29','https://www.court.gov.cn/fabu/xiangqing/282631.html','2021-01-01'),
 ('amend-procedure-19','https://www.court.gov.cn/fabu/xiangqing/282651.html','2021-01-01'),
 ('amend-ip-18','https://policy.mofcom.gov.cn/claw/clawContent.shtml?id=87869','2021-01-01'),
 ('regulations-2024-march','https://app.www.gov.cn/govdata/gov/202403/15/513018/article.html','2024-05-01'),
 ('regulations-2024-dec','https://app.www.gov.cn/govdata/gov/202412/13/522682/articleNew.html','2025-01-20')]
def one(row):
 key,url,effective=row
 try:
  versions,meta,path,title=read_source(url)
  text=max((t for t,s in versions if s),key=len,default=versions[-1][0])
  r=dict(key=key,url=url,effective=effective,title=title,text=text,raw_path='raw/bulk/'+path,source_sha256=meta['sha256'],retrieved_at=meta['retrieved_at'])
  dump(ROOT/f'data/raw/bulk/validity/parsed/{key}.json',r)
  return dict(key=key,ok=True,length=len(text))
 except Exception as e:return dict(key=key,ok=False,error=str(e)[:180])
with ThreadPoolExecutor(max_workers=6) as p:rs=list(p.map(one,SOURCES))
print(json.dumps(rs,ensure_ascii=False))
