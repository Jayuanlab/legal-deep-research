"""Build additive records from archived official texts; never infer effective dates."""
import json,hashlib,sqlite3,shutil,os,re
from datetime import date
from collections import Counter
from pathlib import Path
import corpus
from official_bulk import ROOT,dump
from collect_gap185 import OUT,digest

def generate():
 targets=json.loads((ROOT/'data/gap185-targets.json').read_text(encoding='utf-8'))
 docs=[];sources=[]
 for target in targets:
  r=json.loads((OUT/f"parsed/{digest(target['name'])}.json").read_text(encoding='utf-8'))
  assert r['validation_version']==2 and r['name']==target['name']
  assert hashlib.sha256((corpus.DATA/r['raw_path']).read_bytes()).hexdigest()==r['source_sha256']
  for p in r['parts']:
   article=p['article'];label=p['text'].split()[0] if article else '（全文）'
   if article:label=p['text'].split('条',1)[0]+'条'+(('之'+p['text'].split('条之',1)[1].split()[0]) if '条之' in p['text'][:25] else '')
   d=dict(id='G'+digest(r['name'])[:20]+'A'+(article.replace('之','Z') if article else 'ALL'),doc_type='law',law_name=r['name'],article=article,
    title=r['name']+' '+label,text=p['text'],text_sha256=p['text_sha256'],kind='法律官方转载原文'+('（全文未分条）' if not article else ''),
    url=r['url'],raw_path=r['raw_path'],source_sha256=r['source_sha256'],retrieved_at=r['retrieved_at'],topic='全国性法律',tags=r['name'],
    version=f"官网刊载版本；目录基准{r['required_year']}年；源哈希 {r['source_sha256'][:12]}",date=None,published_at=None,
    version_note=r['edition_evidence'],edition_basis=r['edition_basis'],authority_status='官方刊载版本；现行效力、修订完整性与个案时间适用仍须核验',
    reference_status=r.get('reference_status','unknown'))
   if r.get('source_page_status'):d['authority_status']+='；'+r['source_page_status']
   if r.get('title_binding'):d['title_binding']=r['title_binding']
   effective=re.search(r'本(?:法|条例|决定|规定)自\s*(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日(?:起)?施行',re.sub(r'\s+','',r['parts'][-1]['text']))
   if effective and date(*map(int,effective.groups()))>date(2026,11,13):
    d.update(reference_status='not_reference',date=date(*map(int,effective.groups())).isoformat(),authority_status=d['authority_status']+'；尚未施行，默认不参与研究')
   if r.get('contains_attachment'):d['kind']+='（含附件，附件条文未另行编号）'
   docs.append(d)
  sources.append({k:v for k,v in r.items() if k!='parts'})
 assert len(sources)==185
 dump(corpus.DATA/'laws-gap185.json',docs)
 manifest=dict(targets=185,collected=185,records=len(docs),numbered_articles=sum(d['article'] is not None for d in docs),whole_texts=sum(d['article'] is None for d in docs),
  version_evidence_pending=[s['name'] for s in sources if s['edition_basis']!='原文年份证据'],sources=sources)
 dump(corpus.DATA/'gap185-import-manifest.json',manifest)
 print(json.dumps({k:v for k,v in manifest.items() if k not in ('sources','version_evidence_pending')}),flush=True)

def stage():
 staged=corpus.DATA/'legal-gap185.sqlite3'
 if not staged.exists():
  with corpus.connection() as db:
   old={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
   assert len(old)==44734
   archive=ROOT/'evaluation/archives/before-gap185-20261113';archive.mkdir(exist_ok=False)
   dump(archive/'corpus.json',old)
   for n in ('manifest.json','laws.jsonl','cases.jsonl','controls.jsonl'):shutil.copy2(ROOT/'evaluation'/n,archive/n)
   target=sqlite3.connect(staged)
   try:db.backup(target)
   finally:target.close()
 corpus.DB=staged
 after=corpus.rebuild();print(json.dumps(after),flush=True)
 path=corpus.DATA/'gap185-import-manifest.json';m=json.loads(path.read_text(encoding='utf-8'));m.update(before=dict(laws=42549,cases=2185,total=44734),after=after);dump(path,m)
 os.environ['LEGAL_INDEX_WORKERS']='16';os.environ['LEGAL_INDEX_BATCH_SIZE']='10'
 import vectors
 dump(corpus.DATA/'gap185-index-status.json',vectors.build())

if __name__=='__main__':generate();stage()
