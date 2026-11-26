import json
from collect_gap185 import ROOT,OUT,dump,digest,parse_candidate,read_source
targets=json.loads((ROOT/'data/gap185-targets.json').read_text(encoding='utf-8'))
changes=[
 ('中华人民共和国民族区域自治法','https://xzfy.moj.gov.cn/c/2021-01-06/487588.shtml'),
 ('中华人民共和国反外国制裁法','https://www.hengqin.gov.cn/lab/flfg/fl/content/post_3517850.html'),
 ('全国人民代表大会常务委员会关于在沿海港口城市设立海事法院的决定','https://www.12371.cn/2021/02/01/ARTI1612169824732675.shtml'),
 ('全国人民代表大会常务委员会关于批准中央军事委员会《关于授予军队离休干部中国人民解放军功勋荣誉章的规定》的决定','https://www.12371.cn/2021/02/01/ARTI1612170656082700.shtml')]
for name,url in changes:
 try:
  r=parse_candidate(next(t for t in targets if t['name']==name),url)
  dump(OUT/f'parsed/{digest(name)}.json',r)
  print('OK',name,r['article_count'],r['parts'][-1]['text'][-100:])
 except Exception as e:print('ERROR',name,str(e))
