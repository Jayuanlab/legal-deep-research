import io,json,hashlib
from pathlib import Path
import requests
from pypdf import PdfReader
ROOT=Path(__file__).parent
sources=[('zhonglun-meeting-opinion','https://static.cninfo.com.cn/finalpage/2025-04-22/1223195573.pdf',[0,1,2,4]),('hankun-repurchase-guide','https://www.hankunlaw.com/upload/portal/20250521/c0946be4afdc3ab5caaf16406bbaefee.pdf',[3,4,5,15,25,60])]
for name,url,pages in sources:
 p=ROOT/'references'/(name+'.pdf');p.parent.mkdir(exist_ok=True)
 if not p.exists():
  r=requests.get(url,timeout=45);r.raise_for_status();assert r.content.startswith(b'%PDF');p.write_bytes(r.content)
 raw=p.read_bytes();reader=PdfReader(io.BytesIO(raw))
 text='\n\n'.join(f'PAGE {i+1}\n'+(reader.pages[i].extract_text() or '') for i in pages if i<len(reader.pages))
 (p.with_suffix('.extract.txt')).write_text(text,encoding='utf-8')
 p.with_suffix('.provenance.json').write_text(json.dumps(dict(url=url,sha256=hashlib.sha256(raw).hexdigest(),pages=len(reader.pages),inspected_pages=[i+1 for i in pages]),indent=2),encoding='utf-8')
 print(name,len(reader.pages),repr(text[:700]))
