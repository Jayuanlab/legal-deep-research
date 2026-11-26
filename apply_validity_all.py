"""Publish the full-inventory audit, with an unchanged-text rollback snapshot."""
import json,shutil,hashlib
from collections import Counter
from pathlib import Path
import corpus,vectors
from official_bulk import dump
from law_validity import enrich
from evaluation.build_dataset import corpus_fingerprint
from evaluation.evaluate import load_dataset
ROOT=Path(__file__).parent
def main():
 proposal=json.loads((corpus.DATA/'validity-all-proposal.json').read_text(encoding='utf-8'))
 assert proposal['scanned_records']==52995 and proposal['scanned_source_versions']==1204
 with corpus.connection() as db:
  assert not db.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0],'Active research job'
  before={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
 archive=ROOT/'evaluation/archives/before-validity-all-20261113'
 if not archive.exists():
  archive.mkdir();dump(archive/'corpus.json',before)
  for name in ('manifest.json','laws.jsonl','cases.jsonl','controls.jsonl'):shutil.copy2(ROOT/'evaluation'/name,archive/name)
  shutil.copy2(corpus.DATA/'law-validity.json',archive/'law-validity.json')
 rules=proposal['by_id']
 for k,r in rules.items():
  d=before[k]
  r.update(document_source_sha256=d.get('source_sha256'),document_text_sha256=d.get('text_sha256'),document_version=d.get('version'))
  if r.get('raw_path') and r.get('source_sha256'):
   assert hashlib.sha256((corpus.DATA/r['raw_path']).read_bytes()).hexdigest()==r['source_sha256']
 after={k:enrich(d,rules) for k,d in before.items()}
 for k,d in after.items():assert all(d.get(f)==before[k].get(f) for f in ('title','text','text_sha256','url','source_sha256'))
 positives={q['doc_id'] for name in ('laws','cases','controls') for line in (ROOT/'evaluation'/f'{name}.jsonl').read_text(encoding='utf-8').splitlines() for q in json.loads(line)['qrels']}
 assert not any(after[k].get('reference_status')=='not_reference' for k in positives),'Positive label conflicts with new legal status'
 dump(corpus.DATA/'law-validity.json',dict(as_of=proposal['as_of'],scope=proposal['scope'],by_id=rules))
 with corpus.connection() as db:
  for k,d in after.items():
   if d!=before[k]:db.execute('UPDATE documents SET payload=? WHERE id=?',(json.dumps(d,ensure_ascii=False),k))
 manifest=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))
 manifest.update(corpus_sha256=corpus_fingerprint(after),corpus_revision='validity-all-20261113',corpus_revision_note='全库1204来源版本扫描；新增废止、部分失效和已修改历史版本标记并排除当前研究召回。400题问法、qrel、分组保持且锚点校验通过；未重跑400题，旧成绩不代表本轮成绩。')
 dump(ROOT/'evaluation/manifest.json',manifest);load_dataset()
 counts=dict(Counter(d['validity']['code'] for d in after.values() if d['doc_type']=='law'))
 versions=Counter()
 for row in proposal['audit']:
  for code in row['status_counts']:
   if code!='unknown':versions[code]+=1
 result=dict(as_of=proposal['as_of'],scanned_records=52995,scanned_source_versions=1204,scanned_names=1138,counts=counts,source_versions_with_status=dict(versions),
  newly_excluded=sum(d.get('reference_status')=='not_reference' and before[k].get('reference_status')!='not_reference' for k,d in after.items()),pending_matches=proposal['pending_matches'],vectors=vectors.status(),unchanged_text_records=len(before),research_jobs_preserved=True,scope=proposal['scope'])
 dump(corpus.DATA/'validity-all-report.json',result)
 dump(corpus.DATA/'validity-all-ledger.json',proposal['audit'])
 print(json.dumps({k:v for k,v in result.items() if k not in ('pending_matches',)},ensure_ascii=False))
if __name__=='__main__':main()
