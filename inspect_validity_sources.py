import json,re
from pathlib import Path
for p in Path('data/raw/bulk/validity/parsed').glob('*.json'):
 r=json.loads(p.read_text(encoding='utf-8'));text=r['text']
 print('\nSOURCE',r['key'],len(text),repr(text[:180]))
 print('HEADINGS',re.findall(r'(?m)^[一二三四五六七八九十百]+、[^\n]{0,180}',text)[:4])
 print('FINAL',repr(text[-220:]))
