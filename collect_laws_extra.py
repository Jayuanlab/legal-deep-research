"""Collect official laws and interpretations. Offline by default.

Only --refresh opens network connections. Raw responses are stored unchanged.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'
STATUS = '来源发布版本；当前效力及个案时间适用待核验'
SOURCES = [
    dict(key='labor-contract', law_name='中华人民共和国劳动合同法', offset=20000, count=98,
         url='https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_0abfdd261c03417b949df19d869add8d.html',
         version='2012年修正', published_at='2012-12-28', effective=None,
         version_marker='2012年12月28日', topic='劳动合同',
         final_tail='本法自2008年1月1日起施行。',
         date_note='末条为原法施行日2008-01-01；本次未存档修正决定的施行条款，版本施行日期置null。'),
    dict(key='labor', law_name='中华人民共和国劳动法', offset=21000, count=107,
         url='https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_d9aa750028b14b99a776cb93726a360d.html',
         version='2018年第二次修正', published_at='2018-12-29', effective=None,
         version_marker='2018年12月29日', topic='劳动',
         final_tail='本法自1995年1月1日起施行。',
         date_note='末条为原法施行日1995-01-01；本次未存档修正决定的施行条款，版本施行日期置null。'),
    dict(key='company', law_name='中华人民共和国公司法', offset=22000, count=266,
         url='https://www.samr.gov.cn/xyjgs/flfg/art/2024/art_d4e84936a8a744f8928ac7aec7594345.html',
         version='2023年第二次修订', published_at='2023-12-29', effective='2024-07-01',
         version_marker='2023年12月29日', topic='公司',
         final_tail='具体实施办法由国务院规定。', date_note='版本施行日期依据第二百六十六条，保留其第二款过渡规定。'),
    dict(key='consumer', law_name='中华人民共和国消费者权益保护法', offset=23000, count=63,
         url='https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2023/art_0a323e046fba43f0b6e9e977f1e8d5fc.html',
         version='2013年第二次修正', published_at='2013-10-25', effective=None,
         version_marker='2013年10月25日', topic='消费者权益',
         final_tail='本法自1994年1月1日起施行。',
         date_note='末条为原法施行日1994-01-01；本次未存档修正决定的施行条款，版本施行日期置null。'),
    dict(key='civil-procedure', law_name='中华人民共和国民事诉讼法', offset=24000, count=306,
         url='https://ipc.court.gov.cn/zh-cn/news/view-6231.html',
         version='2023年第五次修正', published_at='2023-09-01', effective=None,
         version_marker='2023年9月1日', topic='民事诉讼',
         final_tail='《中华人民共和国民事诉讼法（试行）》同时废止。',
         date_note='末条为原法施行条款；本次未存档修正决定的施行条款，版本施行日期置null。第144、275条条号后无空格，原样保留。'),
    dict(key='personal-information', law_name='中华人民共和国个人信息保护法', offset=25000, count=74,
         url='https://www.cac.gov.cn/2021-08/20/c_1631050028355286.htm',
         version='2021年通过文本', published_at='2021-08-20', effective='2021-11-01',
         version_marker='2021年8月20日', topic='个人信息保护',
         final_tail='本法自2021年11月1日起施行。', date_note='施行日期依据第七十四条。'),
    dict(key='guarantee-interpretation', law_name='最高人民法院关于适用《中华人民共和国民法典》有关担保制度的解释',
         offset=26000, count=71, kind='司法解释原文',
         url='https://www.court.gov.cn/zixun/xiangqing/282721.html',
         version='法释〔2020〕28号', published_at='2020-12-31', effective='2021-01-01',
         version_marker='2020年12月25日', topic='担保',
         final_tail='本解释自2021年1月1日起施行。', date_note='公布日期依据官方落款；施行日期依据第七十一条。'),
]


class TextParser(HTMLParser):
    """Same block/line approach as ingest.extract_articles; keep every item."""
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.skip += 1
        if tag in ('p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'tr'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if tag in ('p', 'div', 'li', 'tr'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def cn_number(value):
    digits = dict(zip('零一二三四五六七八九', range(10)))
    total = current = 0
    for char in value:
        if char in digits:
            current = digits[char]
        elif char in '十百千':
            total += (current or 1) * {'十': 10, '百': 100, '千': 1000}[char]
            current = 0
        else:
            raise ValueError('无法解析条号')
    return total + current


def page_text(html):
    parser = TextParser()
    parser.feed(html)
    return ''.join(parser.parts).replace('\xa0', ' ')


ARTICLE = re.compile(r'(?:^|\n)[ \t\u3000]*第([零一二三四五六七八九十百千]+)条[ \t\u3000]*')
HEADING = re.compile(r'\n\s*第[零一二三四五六七八九十百千]+[章节编]\s*')


def extract_articles(html, source):
    text = page_text(html)
    matches = list(ARTICLE.finditer(text))
    numbers = [cn_number(m.group(1)) for m in matches]
    expected = list(range(1, source['count'] + 1))
    if numbers != expected:
        raise ValueError(f"{source['key']}: 条号缺漏/重复/乱序: {numbers}; expected 1..{source['count']}")
    if source['version_marker'] not in text[:matches[0].start()]:
        raise ValueError(f"{source['key']}: 未找到预期版本沿革")
    result = {}
    for i, match in enumerate(matches):
        body = text[match.start():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        body = HEADING.split(body)[0]
        body = re.split(r'\n\s*[一二三四五六七八九十]+、',body)[0]
        if i == len(matches) - 1:
            tail = source['final_tail']
            if not tail or tail not in body:
                raise ValueError(f"{source['key']}: 末条终点待核验: {body[:2200]!r}")
            body = body[:body.index(tail) + len(tail)]
        body = '\n'.join(line.strip() for line in body.splitlines() if line.strip())
        if '\ufffd' in body or '???' in body:
            raise ValueError('正文存在乱码')
        result[numbers[i]] = body
    return result


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fetch(source):
    request = urllib.request.Request(source['url'], headers={'User-Agent': 'Mozilla/5.0 (official-law local archival collection)'})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read()
        charset = response.headers.get_content_charset()
        if not charset:
            match = re.search(br'charset\s*=\s*[\"\x27]?([A-Za-z0-9_-]+)', raw[:10000], re.I)
            charset = match.group(1).decode('ascii') if match else 'utf-8'
        metadata = dict(url=source['url'], final_url=response.url, encoding=charset,
                        retrieved_at=datetime.now(timezone.utc).isoformat(), source_sha256=sha256(raw),
                        content_type=response.headers.get('Content-Type'))
    raw.decode(charset)  # Strict decoding, never silently replace characters.
    return raw, metadata


def main(refresh=False, source_key=None):
    raw_dir = DATA / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    docs, manifest = [], []
    for source in SOURCES:
        path = raw_dir / ('extra-' + source['key'] + '.html')
        meta_path = path.with_suffix('.json')
        if refresh and (source_key is None or source_key == source['key']):
            raw, metadata = fetch(source)
            # Preserve actual response, even if structural validation later fails.
            path.write_bytes(raw)
            write_json(meta_path, metadata)
        else:
            raw = path.read_bytes()
            metadata = json.loads(meta_path.read_text(encoding='utf-8'))
        if metadata['source_sha256'] != sha256(raw) or metadata['url'] != source['url']:
            raise ValueError(f'{path.name}: 存档哈希或来源不一致')
        html = raw.decode(metadata['encoding'])
        articles = extract_articles(html, source)
        # Store visible page time separately from legal promulgation and CMS time.
        visible = re.search(r'发布时间[：:]\s*([0-9-]+(?:\s+[0-9:]+)?)', page_text(html))
        if source['key'] == 'personal-information':
            visible = re.search(r'(2021年08月20日\s+21:21)', page_text(html))
        page_published_at = visible.group(1) if visible else None
        cms_date = re.search(r'<meta\s+name=[\"\x27]PubDate[\"\x27]\s+content=[\"\x27]([^\"\x27]+)', html, re.I)
        for number, text in articles.items():
            docs.append(dict(id='E' + str(source['offset'] + number), doc_type='law', kind=source.get('kind','法律原文'),
                             law_name=source['law_name'], article=str(number), title=f"{source['law_name']} 第{number}条",
                             text=text, tags=source['topic'] + ' ' + source['law_name'], topic=source['topic'],
                             date=source['effective'], published_at=source['published_at'], version=source['version'],
                             url=source['url'], retrieved_at=metadata['retrieved_at'], source_sha256=sha256(raw),
                             text_sha256=sha256(text.encode('utf-8')), authority_status=STATUS))
        manifest.append(dict(source, **{k: v for k, v in metadata.items() if k != 'url'},
                             raw_path=path.relative_to(DATA.parent).as_posix(), articles=len(articles),
                             page_published_at=page_published_at,
                             cms_pubdate=cms_date.group(1) if cms_date else None,
                             id_start='E' + str(source['offset'] + 1), id_end='E' + str(source['offset'] + source['count']),
                             authority_status=STATUS))
        print(f"{source['key']}: {len(articles)} articles", flush=True)
    if len({doc['id'] for doc in docs}) != len(docs):
        raise ValueError('重复ID')
    write_json(DATA / 'laws-extra.json', docs)
    write_json(DATA / 'laws-extra-manifest.json', manifest)
    write_sources(manifest)


def write_sources(manifest):
    lines = ['# 增补法律原文来源与核验边界', '',
             '本文件由 collect_laws_extra.py 根据本地存档生成。默认运行仅离线读取；显式 --refresh 才采集。', '',
             '独立解析沿用 ingest.py 的 HTML 块级换行及中文条号思路，避免导入其数据库依赖。严格检查条号从1至末条连续、无重复、无乱序；删除章节目标题及末条之后的页脚，保留各款项。原始HTTP响应字节不改写，source_sha256覆盖原始字节；text_sha256覆盖规范化条文UTF-8字节。', '',
             'published_at 表示本次版本法律公布日期，不采用网页转载日期。date 表示本次版本施行日期，不确定即null；末条保留的最初施行日不能直接当成修正版本施行日。网页时间另见各来源记录。', '',
             '仅证明存档所载版本及结构完整，不证明采集日或研究日仍为最新现行法；当前效力、后续修法、过渡安排及个案时间适用待核验。研究阶段不联网，不调用向量模型，不写SQLite或现有laws.json。', '']
    for entry in manifest:
        lines += [f"## {entry['law_name']}（{entry['version']}）", '',
                  f"- 官方来源：[{entry['url']}]({entry['url']})",
                  f"- 公布日期：{entry['published_at']}；版本施行日期：{entry['effective'] or 'null'}。{entry['date_note']}",
                  f"- 网页可见发布时间：{entry.get('page_published_at') or '未确认（不从URL推断）'}；CMS PubDate：{entry.get('cms_pubdate') or 'null'}（可能为迁移/更新，与法律公布日期无关）。",
                  f"- 条数：{entry['articles']}；编号：{entry['id_start']}—{entry['id_end']}。",
                  f"- 采集时间（UTC）：{entry['retrieved_at']}；解码：{entry['encoding']}。",
                  f"- 存档：`{entry['raw_path']}`；原文SHA256：`{entry['source_sha256']}`。",
                  f"- 末条截断锚点：{entry['final_tail']}", '']
    (DATA / 'extra-laws-sources.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true', help='Explicitly download official pages; default is offline archives.')
    parser.add_argument('--source', choices=[s['key'] for s in SOURCES], help='Refresh only this source; other sources use archives.')
    args=parser.parse_args()
    if args.source and not args.refresh:parser.error('--source requires --refresh')
    main(args.refresh,args.source)
