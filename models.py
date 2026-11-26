"""Read Zhiyu deployment profiles without copying or returning credentials."""
import hashlib
import json
import math
import os
import urllib.error
import urllib.request
import uuid
import time
import ssl
import http.client
from pathlib import Path
from dotenv import dotenv_values

SETTINGS=Path(__file__).with_name('model-settings.json')


class ModelError(Exception):
    pass


class ModelServiceError(ModelError):
    """Safe provider diagnostics, with no response bodies or credentials."""
    def __init__(self,code,service='model',attempts=1,retryable=False,status=None):
        self.code=code;self.service=service;self.attempts=attempts;self.retryable=retryable;self.status=status
        label={'embedding':'向量模型','text':'语言模型'}.get(service,'模型')
        reason={'timeout':'请求超过时间预算','tls':'TLS握手失败，连接被提前关闭','certificate':'TLS证书校验失败',
                'connection':'连接失败','non_json':'响应不是有效 JSON','response_shape':'响应不是 JSON 对象',
                'http':f'服务返回 HTTP {status}'}.get(code,'请求失败')
        super().__init__(f'{label}{reason}（已尝试{attempts}次）。')


def transport_error(error):
    reason=error.reason if isinstance(error,urllib.error.URLError) else error
    if isinstance(reason,ssl.SSLCertVerificationError):return 'certificate',False
    if isinstance(reason,TimeoutError):return 'timeout',True
    if isinstance(reason,ssl.SSLError):return 'tls',True
    return 'connection',True


def environment():
    root=Path(os.environ.get('ZHIYU_PROJECT_ROOT','D:/zhiyu'))/'apps'/'web'
    env={}
    for name in ('.env','.env.development','.env.local','.env.development.local'):
        path=root/name
        if path.exists(): env.update({k:v for k,v in dotenv_values(path,interpolate=False).items() if v is not None})
    env.update(os.environ)
    def resolve(key,seen=None):
        seen=set() if seen is None else seen
        if key in seen: return ''
        seen.add(key); value=str(env.get(key,'')).strip()
        if value.startswith('$') and value[1:].replace('_','').isalnum(): return resolve(value[1:],seen)
        return '' if value in ('null','undefined','****') else value
    return {key:resolve(key) for key in env}


def config():
    env=environment()
    # The demo intentionally selects Zhiyu's deployed text profile, not user DB settings.
    prefix='LEGAL' if env.get('LEGAL_API_KEY') else 'INTERACTION_PROCESSOR_LLM'
    text=dict(key=env.get(prefix+'_API_KEY',''),base=env.get(prefix+'_BASE_URL',env.get('LEGAL_API_BASE','')).rstrip('/'),
              model=env.get(prefix+'_MODEL',''),protocol=env.get(prefix+'_PROVIDER',env.get('LEGAL_PROTOCOL','openai_compatible')))
    if text['model']=='qwen3.7-plus' and text['base'] in ('https://opencode.ai/zen/go','https://opencode.ai/zen/go/v1','https://opencode.ai/inference/go/anthropic/v1','https://opencode.ai/inference/go/anthropic'):
        text.update(base='https://opencode.ai/inference/go/anthropic',protocol='anthropic_compatible')
    base=env.get('LLM_EMBEDDING_BASE_URL','').rstrip('/')
    key=env.get('OPENAI_EMBEDDINGS_API_KEY','')
    if not key and 'aliyuncs.com' in base: key=env.get('DASHSCOPE_API_KEY','') or env.get('BAILIAN_API_KEY','')
    embed=dict(key=key,base=base,model=env.get('LLM_EMBEDDING_MODEL',''),dimensions=int(env.get('LLM_EMBEDDING_DIMENSIONS','1024')),
               protocol=env.get('LLM_EMBEDDING_API_FORMAT','openai'))
    settings={}
    if SETTINGS.exists():
        try:
            settings=json.loads(SETTINGS.read_text(encoding='utf-8')).get('embedding',{})
            if not isinstance(settings,dict):raise ValueError()
        except (ValueError,OSError,AttributeError):raise ModelError('本地 model-settings.json 的向量模型配置无效。') from None
    provider=env.get('LEGAL_EMBEDDING_PROVIDER') or settings.get('provider','zhiyu')
    if provider=='aliyun':
        try:dimensions=int(env.get('LEGAL_EMBEDDING_DIMENSIONS') or settings.get('dimensions',1024))
        except (TypeError,ValueError):raise ModelError('阿里云向量维度配置无效。') from None
        model=env.get('LEGAL_EMBEDDING_MODEL') or settings.get('model','text-embedding-v4')
        if model=='text-embedding-v4' and dimensions not in (64,128,256,512,768,1024,1536,2048):raise ModelError('text-embedding-v4 的向量维度不受支持。')
        embed=dict(key=env.get('DASHSCOPE_API_KEY') or env.get('BAILIAN_API_KEY',''),
            base=(env.get('LEGAL_EMBEDDING_BASE_URL') or settings.get('base_url','https://dashscope.aliyuncs.com/compatible-mode/v1')).rstrip('/'),
            model=model,dimensions=dimensions,protocol='openai')
    elif provider!='zhiyu':raise ModelError('未知向量模型配置，支持 aliyun 或 zhiyu。')
    return text,embed


def request_json(url,key,payload,headers=None,timeout=120,service='model'):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs): return None
    request=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={
        'Content-Type':'application/json','Authorization':'Bearer '+key,'User-Agent':'legal-research-demo/0.2',**(headers or {})})
    deadline=time.monotonic()+timeout
    for attempt in range(1,6):
        code=None;retryable=False;status=None;delay=0
        try:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise ModelServiceError('timeout',service,attempt-1,True)
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=remaining) as response:
                data=json.load(response)
            if not isinstance(data,dict):raise ModelServiceError('response_shape',service,attempt,False)
            return data
        except urllib.error.HTTPError as error:
            status=error.code; retry=error.headers.get('Retry-After','');error.close()
            code='http';retryable=status in (408,429,500,502,503,504)
            delay=min(30,max(3*(2**(attempt-1)),int(retry) if retry.isdigit() else 0)) if status==429 else min(8,2**(attempt-1))
        except (json.JSONDecodeError,UnicodeDecodeError):
            code='non_json';retryable=True;delay=min(4,2**(attempt-1))
        except (urllib.error.URLError,TimeoutError,OSError,http.client.HTTPException) as error:
            code,retryable=transport_error(error);delay=min(4,2**(attempt-1))
        maximum=5 if status==429 else 3
        if not retryable or attempt>=maximum or delay>=deadline-time.monotonic():
            raise ModelServiceError(code,service,attempt,retryable,status) from None
        time.sleep(delay)


def require(c):
    if not all(c.get(k) for k in ('key','base','model')):
        raise ModelError('Zhiyu 模型配置不完整。请检查项目位置及服务端配置。')


def embedding_identity(c=None):
    c=c or config()[1]
    return hashlib.sha256(json.dumps({k:c[k] for k in ('base','model','dimensions','protocol')},sort_keys=True).encode()).hexdigest()


def embed(texts,query=False,timeout=120):
    c=config()[1]; require(c)
    payload=dict(model=c['model'],input=texts,encoding_format='float',dimensions=c['dimensions'])
    if c['base']=='https://api.jina.ai/v1':
        payload.update(task='retrieval.query' if query else 'retrieval.passage',normalized=True)
    if c['protocol']=='dashscope':
        raise ModelError('当前适配的是 Zhiyu 已配置的 OpenAI 兼容向量接口。')
    data=request_json(c['base']+'/embeddings',c['key'],payload,timeout=timeout,service='embedding')
    try:
        items=sorted(data['data'],key=lambda row:row['index'])
        if [r['index'] for r in items]!=list(range(len(texts))): raise ValueError()
        vectors=[r['embedding'] for r in items]
        for vector in vectors:
            if len(vector)!=c['dimensions'] or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in vector): raise ValueError()
            norm=math.sqrt(sum(v*v for v in vector))
            if norm==0: raise ValueError()
            vector[:]=[v/norm for v in vector]
        return vectors
    except (KeyError,TypeError,ValueError):
        raise ModelError('向量响应的数量、索引、维度或数值无效。') from None


def complete(system,prompt,max_tokens=4000,timeout=120):
    c=config()[0];require(c)
    if c['protocol']=='anthropic_compatible':
        url=c['base']+('/messages' if c['base'].endswith('/v1') else '/v1/messages')
        headers={'x-api-key':c['key'],'anthropic-version':'2023-06-01','x-opencode-session':'legal-'+str(uuid.uuid4())}
        data=request_json(url,c['key'],dict(model=c['model'],system=system,messages=[dict(role='user',content=prompt)],max_tokens=max_tokens),headers,timeout=timeout,service='text')
        if data.get('stop_reason')!='end_turn': raise ModelError('模型未完整结束报告，请增加输出预算或缩小问题。')
        content='\n'.join(item['text'] for item in data.get('content',[]) if item.get('type')=='text')
    elif c['protocol']=='openai_compatible':
        data=request_json(c['base']+'/chat/completions',c['key'],dict(model=c['model'],messages=[dict(role='system',content=system),dict(role='user',content=prompt)],max_tokens=max_tokens,temperature=0.2),timeout=timeout,service='text')
        choice=data['choices'][0]
        if choice.get('finish_reason')!='stop': raise ModelError('模型未完整结束报告。')
        content=choice['message']['content']
    else:
        raise ModelError('文本模型协议尚未适配。')
    if not isinstance(content,str) or not content.strip(): raise ModelError('模型返回空报告。')
    return content,c['model']


def public_config():
    text,embedding=config()
    return dict(text_model=text['model'],text_protocol=text['protocol'],embedding_model=embedding['model'],dimensions=embedding['dimensions'],
                configured=all(c.get(k) for c in (text,embedding) for k in ('key','base','model')))


if __name__=='__main__':
    print(json.dumps(public_config(),ensure_ascii=False))
