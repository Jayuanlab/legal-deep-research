"""Apply narrowly scoped archival cleanup; retain whole-resolution identity."""
import json,hashlib,re
from collect_gap185 import OUT,clean_text,dump
for p in (OUT/'parsed').glob('*.json'):
 r=json.loads(p.read_text(encoding='utf-8'))
 for part in r['parts']:
  part['text']=clean_text(part['text'])
  part['text_sha256']=hashlib.sha256(part['text'].encode()).hexdigest()
 # An approval resolution's attachment is separately titled. Avoid presenting
 # the annex's historical rules as provisions of the approval resolution.
 if r['article_count']==0 and '关于批准' in r['name']:
  text=r['parts'][0]['text']
  text=re.split(r'\n(?:附[：:]|国务院关于职工探亲待遇的规定|广东省经济特区条例|中华人民共和国中央军事委员会关于授予|关于授予军队离休干部)',text,maxsplit=1)[0].rstrip()
  if '第一条' in text:
   # Preserve annex when its exact heading boundary is not explicit; label it.
   r['contains_attachment']=True
  else:r['parts']=[dict(article=None,text=text,text_sha256=hashlib.sha256(text.encode()).hexdigest())]
 dump(p,r)
print('Normalized',len(list((OUT/'parsed').glob('*.json'))),'archived texts')
