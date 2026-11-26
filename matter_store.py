"""Local case files. Digital statements are not authenticated facts."""
import base64,hashlib,io,json,re,uuid,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
from corpus import connection
from models import ModelError

STORE=Path(__file__).parent/'data'/'matters'
GOALS={'undecided':'尚未确认','performance':'继续取得履行','exit':'退出交易并研究退款','settlement':'优先协商解决'}
ROLES={'unknown':'尚未确认','buyer':'买方／采购方','supplier':'供应商／卖方'}
KINDS={'contract','notice','communication','payment','other'}
MAX_FILE=8*1024*1024

def setup():
 with connection() as db:
  db.execute('CREATE TABLE IF NOT EXISTS matters(id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
  db.execute('CREATE TABLE IF NOT EXISTS matter_files(id TEXT PRIMARY KEY,matter_id TEXT NOT NULL,payload TEXT NOT NULL)')

def key(value):
 if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{32}',value):raise ModelError('无效案件或材料编号。')
 return value

def profile(data):
 goal=data.get('goal','undecided');role=data.get('client_role','unknown');constraints=data.get('constraints','')
 if goal not in GOALS or role not in ROLES or not isinstance(constraints,str) or len(constraints)>1200:raise ModelError('客户目标、立场或约束输入无效。')
 return dict(goal=goal,client_role=role,constraints=constraints.strip())

def create(data):
 setup();name=data.get('name','未命名案件')
 if not isinstance(name,str) or not 1<=len(name.strip())<=120:raise ModelError('案件名称应为1至120字。')
 item=dict(id=uuid.uuid4().hex,name=name.strip(),created_at=datetime.now(timezone.utc).isoformat(),**profile(data))
 with connection() as db:db.execute('INSERT INTO matters VALUES(?,?)',(item['id'],json.dumps(item,ensure_ascii=False)))
 return get(item['id'])

def get(matter_id):
 setup();key(matter_id)
 with connection() as db:
  row=db.execute('SELECT payload FROM matters WHERE id=?',(matter_id,)).fetchone()
  docs=[json.loads(r[0]) for r in db.execute('SELECT payload FROM matter_files WHERE matter_id=? ORDER BY rowid',(matter_id,))]
 if not row:raise ModelError('案件不存在。')
 return dict(json.loads(row[0]),documents=[public_document(d) for d in docs])

def list_matters():
 setup()
 with connection() as db:return [json.loads(r[0]) for r in db.execute('SELECT payload FROM matters ORDER BY rowid DESC LIMIT 100')]

def public_document(d):
 return {k:v for k,v in d.items() if k!='storage_path'}

def extract(name,data):
 suffix=Path(name).suffix.lower();parts=[]
 if suffix in ('.txt','.md'):
  try:text=data.decode('utf-8-sig')
  except UnicodeDecodeError:raise ModelError('文本材料请使用UTF-8编码。') from None
  parts=[('段落 '+str(i),t) for i,t in enumerate(re.split(r'\n\s*\n',text),1) if t.strip()]
 elif suffix=='.docx':
  try:
   with zipfile.ZipFile(io.BytesIO(data)) as z:
    entry=z.getinfo('word/document.xml')
    if len(z.infolist())>2000 or entry.file_size>8*1024*1024:raise ModelError('DOCX内容超过解析上限。')
    xml=z.read(entry)
   root=ET.fromstring(xml);ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
   parts=[('段落 '+str(i),''.join(t.text or '' for t in p.findall('.//w:t',ns))) for i,p in enumerate(root.findall('.//w:p',ns),1)]
  except (zipfile.BadZipFile,KeyError,ET.ParseError,RuntimeError):raise ModelError('DOCX损坏或无法读取正文。') from None
 elif suffix=='.pdf':
  from pypdf import PdfReader
  try:
   reader=PdfReader(io.BytesIO(data))
   if reader.is_encrypted:raise ModelError('暂不支持加密PDF，请先提供可读取的副本。')
   if len(reader.pages)>100:raise ModelError('单份PDF最多100页。')
   for i,page in enumerate(reader.pages,1):
    content=page.get_contents()
    if content is not None and len(content.get_data())>12*1024*1024:raise ModelError('PDF页面内容过大。')
    parts.append(('第'+str(i)+'页',page.extract_text() or ''))
    if sum(len(t) for _,t in parts)>120000:raise ModelError('单份材料文字最多12万字符。')
  except ModelError:raise
  except Exception:raise ModelError('PDF无法解析，请提供可提取文字的副本。') from None
 else:raise ModelError('支持UTF-8 TXT/MD、DOCX及文字型PDF。')
 if sum(len(t) for _,t in parts)>120000:raise ModelError('单份材料文字最多12万字符。')
 spans=[]
 for location,text in parts:
  text=text.replace('\x00','').strip()
  if not text:continue
  for start in range(0,len(text),1000):spans.append(dict(location=location+(' · 片段'+str(start//1000+1) if len(text)>1000 else ''),text=text[start:start+1000],offset=start))
 if len(spans)>300:raise ModelError('单份材料片段过多，请拆分后上传。')
 return spans

def upload(matter_id,data):
 matter=get(matter_id);name=data.get('name');kind=data.get('kind','other');encoded=data.get('content_base64')
 if not isinstance(name,str) or not 1<=len(name)<=160 or re.search(r'[/\\\x00\r\n]',name):raise ModelError('无效材料名称。')
 if kind not in KINDS or not isinstance(encoded,str) or len(encoded)>MAX_FILE*4//3+8:raise ModelError('材料类型或大小无效。')
 try:raw=base64.b64decode(encoded,validate=True)
 except ValueError:raise ModelError('材料编码无效。') from None
 if not 1<=len(raw)<=MAX_FILE:raise ModelError('单份材料应在8MB以内。')
 digest=hashlib.sha256(raw).hexdigest()
 for old in matter['documents']:
  if old['sha256']==digest:return old
 if len(matter['documents'])>=12:raise ModelError('每案最多12份材料。')
 spans=extract(name,raw);file_id=uuid.uuid4().hex
 for i,span in enumerate(spans,1):span.update(id='U'+file_id+'_'+str(i),material_id=file_id,name=name)
 folder=STORE/key(matter_id);folder.mkdir(parents=True,exist_ok=True);path=folder/(file_id+Path(name).suffix.lower());path.write_bytes(raw)
 item=dict(id=file_id,matter_id=matter_id,name=name,kind=kind,sha256=digest,uploaded_at=datetime.now(timezone.utc).isoformat(),status='text_extracted_unverified' if spans else 'needs_ocr',spans=spans,storage_path=str(path))
 with connection() as db:db.execute('INSERT INTO matter_files VALUES(?,?,?)',(file_id,matter_id,json.dumps(item,ensure_ascii=False)))
 return public_document(item)

def snapshot(matter_id,selected=None,overrides=None):
 matter=get(matter_id)
 if selected is not None:
  if not isinstance(selected,list) or any(not isinstance(x,str) for x in selected):raise ModelError('材料选择无效。')
  known={d['id'] for d in matter['documents']}
  if set(selected)-known:raise ModelError('所选材料不属于本案。')
  matter['documents']=[d for d in matter['documents'] if d['id'] in selected]
 if overrides is not None:matter.update(profile(overrides))
 return matter
