"""Resumable build-time archival of public official sources; never imported by research."""
import hashlib,json,re,time,urllib.request,urllib.error
import threading
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).parent
RAW=ROOT/'data/raw/bulk'
RAW.mkdir(parents=True,exist_ok=True)
DOMAINS=('npc.gov.cn','court.gov.cn','moj.gov.cn','samr.gov.cn','chinatax.gov.cn','sdcourt.gov.cn','81.cn','12371.cn','flkoss.obs-bj2.cucloud.cn')
BLOCKED_ORIGINS=set()
BLOCK_LOCK=threading.Lock()

def allowed(url):
    host=urlparse(url).hostname or ''
    return url.startswith('https://') and (host=='gov.cn' or host.endswith('.gov.cn') or any(host==d or host.endswith('.'+d) for d in DOMAINS))

def dump(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)

def fetch(url,name,payload=None,refresh=False,timeout=35,retries=3,origin_circuit=True):
    if not allowed(url):raise ValueError('Nonofficial URL')
    path=RAW/name;meta_path=path.with_suffix(path.suffix+'.meta.json')
    if path.exists() and meta_path.exists() and not refresh:
        raw=path.read_bytes();meta=json.loads(meta_path.read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest()!=meta['sha256']:raise ValueError('Archive hash mismatch')
        return raw,meta
    origin=urlparse(url).hostname
    with BLOCK_LOCK:
        if origin_circuit and origin in BLOCKED_ORIGINS:raise RuntimeError('Official origin returned an access/redirect barrier earlier in this process; downloads paused')
    for attempt in range(retries):
        try:
            req=urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'User-Agent':'Mozilla/5.0 (LocalOfficialLegalArchive)','Content-Type':'application/json','Referer':'https://flk.npc.gov.cn/'})
            with urllib.request.urlopen(req,timeout=timeout) as r:
                if not allowed(r.url):raise ValueError('Unreviewed redirect')
                raw=r.read();ctype=r.headers.get('Content-Type','')
            # The request endpoint is retained, not expiring download authorization.
            saved_url=url.split('?')[0] if 'cucloud.cn' in urlparse(url).hostname else url
            meta=dict(url=saved_url,retrieved_at=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(raw).hexdigest(),content_type=ctype)
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);dump(meta_path,meta)
            return raw,meta
        except urllib.error.HTTPError as e:
            if e.code in (301,302,303,307,308,401,403,451):
                if origin_circuit:
                    with BLOCK_LOCK:BLOCKED_ORIGINS.add(origin)
                raise
            if attempt==retries-1:raise
            time.sleep(attempt+1)
        except (TimeoutError,urllib.error.URLError):
            if attempt==retries-1:raise
            time.sleep(attempt+1)

def json_fetch(url,name,payload=None):
    raw,meta=fetch(url,name,payload)
    obj=json.loads(raw)
    if obj.get('code')!=200:raise ValueError('Official API returned '+str(obj.get('code')))
    return obj,meta
