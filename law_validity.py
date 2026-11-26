"""Evidence-backed metadata overlay, independent of original text and vectors."""
import json,re
from pathlib import Path
DATA=Path(__file__).parent/'data'
LABELS={'repealed':'已废止／失效','partially_repealed':'部分条款已废止','superseded':'已修改的历史版本','not_yet_effective':'尚未施行','needs_review':'效力存疑，待核验','unknown':'效力待核验'}
def norm(s):return re.sub(r'[\s《》〈〉“”"（）()〔〕\[\]：:]','',s)
def instrument(s):
 m=re.search(r'法释[〔\[（(](\d{4})[〕\]）)]\s*(\d+)\s*号',s)
 return tuple(m.groups()) if m else None
def load_rules():
 p=DATA/'law-validity.json'
 return json.loads(p.read_text(encoding='utf-8')).get('by_id',{}) if p.exists() else {}
def enrich(d,rules):
 if d['doc_type']!='law':return d
 status=rules.get(d['id'],dict(code='unknown',label=LABELS['unknown'],reason='尚未完成该发布版本的现行效力清理；不能据收录推定有效。',checked_at=None))
 if any(status.get(bound) is not None and status[bound]!=d.get(field) for bound,field in [('document_source_sha256','source_sha256'),('document_text_sha256','text_sha256'),('document_version','version')]):
  status=dict(code='unknown',label=LABELS['unknown'],reason='发布版本或原文已变更，旧效力依据不能直接沿用，须重新核验。',checked_at=None)
 out=dict(d,validity=status)
 if status['code'] in ('repealed','partially_repealed','superseded'):out['reference_status']='not_reference'
 return out
def classify(d,source,as_of='2026-11-13'):
 row=next((r for r in source['rows'] if norm(r[1])==norm(d['law_name'])),None)
 base=dict(checked_at=as_of,scope='该条目对应的发布版本')
 if row and instrument(d.get('version','')) and instrument(d.get('version',''))==instrument(row[2]):
  return dict(base,code='repealed',label=LABELS['repealed'],effective_from=source['effective'],reason='名称和发布文号同时匹配法释〔2020〕16号所附废止目录；历史案件的时间适用仍须另行审查。',source_url=source['url'],raw_path=source['raw_path'],source_sha256=source['source_sha256'],notice_entry=row)
 if d.get('status_source') and '第一款' in d.get('authority_status','') and '废止' in d['authority_status']:
  return dict(base,code='partially_repealed',label=LABELS['partially_repealed'],scope='仅本条第一款；未认定整部解释废止',reason=d['authority_status'],effective_from=d.get('status_effective'),source_url=d['status_source'])
 if d.get('date') and d['date']>as_of and '尚未施行' in d.get('authority_status',''):
  return dict(base,code='not_yet_effective',label=LABELS['not_yet_effective'],reason=d['authority_status'],effective_from=d['date'],source_url=d['url'],raw_path=d.get('raw_path'),source_sha256=d.get('source_sha256'))
 if d.get('reference_status')=='not_reference':
  return dict(base,code='needs_review',label=LABELS['needs_review'],reason=d.get('authority_status','当前默认不参与研究，效力尚须核验'),source_url=d['url'])
 if row:return dict(base,code='needs_review',label=LABELS['needs_review'],reason='名称匹配废止目录，但版本文号未匹配，不能直接认定该发布版本废止。',source_url=source['url'])
 return None
