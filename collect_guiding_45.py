"""Fill the missing guide using a court's official republication; preserve provenance."""
import hashlib
from bs4 import BeautifulSoup
from official_bulk import ROOT,fetch,dump
from collect_cases import parse_case

if __name__=='__main__':
    url='https://www.sdcourt.gov.cn/tadpfy/369377/369381/1497619/index.html'
    raw,meta=fetch(url,'guiding-45.html');node=BeautifulSoup(raw,'html.parser').select_one('#Zoom')
    if node is None:raise ValueError('Official case body missing')
    title='指导案例45号：北京百度网讯科技有限公司诉青岛奥商网络技术有限公司等不正当竞争纠纷案'
    proxy=('<div class="detail"><div class="title">'+title+'</div></div><div class="txt_txt">'+str(node)+'</div>').encode()
    doc=parse_case(proxy,url,45)
    doc.update(raw_path='raw/bulk/guiding-45.html',source_sha256=hashlib.sha256(raw).hexdigest(),retrieved_at=meta['retrieved_at'],
       kind='指导案例官方法院转载原文（非判决全文）',reference_status='unverified',authority_status='山东法院官网转载最高法院指导案例45号；当前参照状态及个案适用待核验')
    assert doc['date']=='2015-04-15' and doc['points'] and doc['holding']
    dump(ROOT/'data/cases-guiding-extra.json',[doc]);print(doc['id'],len(doc['text']),doc['date'])
