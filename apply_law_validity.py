"""Reversible metadata update; no law text or vector content is rewritten."""
import json,hashlib,shutil
from collections import Counter
from pathlib import Path
import corpus
from law_validity import classify,enrich
from official_bulk import dump
from evaluation.build_dataset import corpus_fingerprint
from evaluation.evaluate import load_dataset
ROOT=Path(__file__).parent
def main():
 if (corpus.DATA/'validity-all-report.json').exists():raise ValueError('已完成全库扫描；请使用 audit_validity_all.py 和 apply_validity_all.py，避免用首轮目录覆盖后续核验。')
 source=json.loads((corpus.DATA/'law-validity-repeal-source.json').read_text(encoding='utf-8'))
 assert len(source['rows'])==116
 assert hashlib.sha256((corpus.DATA/source['raw_path']).read_bytes()).hexdigest()==source['source_sha256']
 with corpus.connection() as db:
  assert not db.execute("SELECT count(*) FROM research_jobs WHERE status IN ('queued','running')").fetchone()[0],'Active research job'
  before={k:json.loads(v) for k,v in db.execute('SELECT id,payload FROM documents')}
 archive=ROOT/'evaluation/archives/before-validity-20261113'
 if not archive.exists():
  archive.mkdir();dump(archive/'corpus.json',before)
  for name in ('manifest.json','laws.jsonl','cases.jsonl','controls.jsonl'):shutil.copy2(ROOT/'evaluation'/name,archive/name)
 rules={d['id']:s for d in before.values() if d['doc_type']=='law' and (s:=classify(d,source))}
 after={k:enrich(d,rules) for k,d in before.items()}
 for k,d in after.items():assert all(d.get(f)==before[k].get(f) for f in ('id','title','text','text_sha256','url','source_sha256'))
 positives={q['doc_id'] for name in ('laws','cases','controls') for line in (ROOT/'evaluation'/f'{name}.jsonl').read_text(encoding='utf-8').splitlines() for q in json.loads(line)['qrels']}
 assert not any(after[k].get('reference_status')=='not_reference' for k in positives),'A positive label needs independent review'
 dump(corpus.DATA/'law-validity.json',dict(as_of='2026-11-13',scope='116件明确废止目录、已归档的部分废止及施行日期；不是全库效力清理完成',by_id=rules))
 with corpus.connection() as db:
  for k,d in after.items():
   if d!=before[k]:db.execute('UPDATE documents SET payload=? WHERE id=?',(json.dumps(d,ensure_ascii=False),k))
 manifest=json.loads((ROOT/'evaluation/manifest.json').read_text(encoding='utf-8'))
 manifest.update(corpus_sha256=corpus_fingerprint(after),corpus_revision='law-validity-20261113',corpus_revision_note='新增有来源的效力标记，废止版本默认不召回；400题问法、标注和分组不变，锚点已核对。原成绩属于标记前快照，未重跑400题。')
 dump(ROOT/'evaluation/manifest.json',manifest);load_dataset()
 result=dict(as_of='2026-11-13',counts=dict(Counter(d['validity']['code'] for d in after.values() if d['doc_type']=='law')),repealed_norms=sorted({d['law_name'] for d in after.values() if d.get('validity',{}).get('code')=='repealed'}),newly_excluded=sum(before[k].get('reference_status')!='not_reference' and d.get('reference_status')=='not_reference' for k,d in after.items()),old_documents=len(before),text_and_vectors_changed=False)
 dump(corpus.DATA/'law-validity-report.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
