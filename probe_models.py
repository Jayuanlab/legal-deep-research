"""Bounded provider probe; prints exception categories, never raw bodies/keys."""
import argparse
import json
import time
from unittest.mock import patch
import models

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--text',action='store_true');parser.add_argument('--direct',action='store_true');args=parser.parse_args()
    start=time.monotonic()
    try:
        if args.text:
            text,model=models.complete('只返回JSON对象。','返回 {"ok":true}',max_tokens=80,timeout=30)
            value=json.loads(text);assert value.get('ok') is True
        else:
            if args.direct:
                original=models.urllib.request.build_opener
                with patch.object(models.urllib.request,'build_opener',side_effect=lambda *handlers:original(models.urllib.request.ProxyHandler({}),*handlers)):
                    value=models.embed(['合同解除催告通知'],query=True,timeout=20)
            else:value=models.embed(['合同解除催告通知'],query=True,timeout=30)
            assert len(value)==1
        print(json.dumps(dict(ok=True,service='text' if args.text else 'embedding',elapsed=round(time.monotonic()-start,2)),ensure_ascii=False))
    except Exception as error:
        chain=[];e=error
        while e is not None:
            row=dict(type=type(e).__name__)
            if isinstance(e,json.JSONDecodeError):row.update(body_chars=len(e.doc),html=e.doc.lstrip().startswith('<'),position=e.pos)
            if isinstance(e,models.ModelError):row['safe_message']=str(e)
            if isinstance(e,models.urllib.error.URLError):row['reason_type']=type(e.reason).__name__
            chain.append(row);e=e.__context__
        print(json.dumps(dict(ok=False,service='text' if args.text else 'embedding',elapsed=round(time.monotonic()-start,2),exceptions=chain),ensure_ascii=False))
        raise SystemExit(1)

if __name__=='__main__':main()
