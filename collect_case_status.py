"""Archive explicitly checked SPC withdrawal notices at build time."""
import argparse
import hashlib
import json
import re
from datetime import datetime,timezone
from bs4 import BeautifulSoup
from collect_cases import fetch,CACHE
from ingest import TextParser
from corpus import DATA

NOTICES=[
    dict(url='https://www.court.gov.cn/fabu/xiangqing/282441.html',numbers=[9,20],effective='2021-01-01',version='法〔2020〕343号'),
    dict(url='https://www.court.gov.cn/zixun/xiangqing/508031.html',numbers=[123,136,139,204],effective='2026-08-15',version='法〔2026〕119号'),
]


def main(refresh=False):
    CACHE.mkdir(parents=True,exist_ok=True);notices=[]
    for notice in NOTICES:
        filename='status-'+notice['effective']+'.html'
        raw=fetch(notice['url'],filename,refresh)
        node=BeautifulSoup(raw,'html.parser').select_one('.txt_txt')
        if node is None:raise ValueError('Missing notice body')
        p=TextParser();p.feed(str(node));text=''.join(p.parts).strip()
        normalized=re.sub(r'\s+','',text)
        if '不再参照' not in text or any(str(n)+'号' not in normalized for n in notice['numbers']):
            raise ValueError('Notice content must be reviewed')
        notices.append(dict(notice,text=text,source_sha256=hashlib.sha256(raw).hexdigest(),raw_path='raw/guiding-cases/'+filename))
    docs=json.loads((DATA/'cases.json').read_text(encoding='utf-8'))
    for d in docs:
        n=int(re.search(r'\d+',d['guiding_number'])[0])
        notice=next((x for x in notices if n in x['numbers']),None)
        if notice:
            d.update(reference_status='not_reference',status_notice_url=notice['url'],status_effective=notice['effective'],
                     authority_status=f"已核对官方通知：自{notice['effective']}起不再参照；不等同于原裁判失效")
        else:d['reference_status']='unverified'
    (DATA/'cases.json').write_text(json.dumps(docs,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(notices=notices,checked_at=datetime.now(timezone.utc).isoformat(),withdrawn_count=sum(d['reference_status']=='not_reference' for d in docs),
                scope='仅核验列明通知，未声称其他案例参照状态已全量核验。')
    (DATA/'case-status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(withdrawn_count=report['withdrawn_count'],notice_count=len(notices))))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true');main(parser.parse_args().refresh)
