"""Check frozen-v1 parity and an explicit offline v2 sample, without re-running all 400."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.evaluate import load_dataset,run
from evaluation.build_dataset import digest
from models import embedding_identity

ROOT=Path(__file__).parent
IDS=['L001','L011','L012','L049','L080','L120','L160','L200','C001','C025','C060','C100','C140','C176','N017','N024']

def main():
    rows,manifest,_=load_dataset()
    baseline=json.loads((ROOT/'results/summary.json').read_text(encoding='utf-8'))
    if baseline['embedding_identity']!=embedding_identity():raise ValueError('This verifier requires the same model as the frozen baseline; use embedding-model comparison for cross-model evaluation')
    before=[json.loads(line) for line in (ROOT/'archives/retrieval-v1/results/details.jsonl').read_text(encoding='utf-8').splitlines()]
    full=[json.loads(line) for line in (ROOT/'results/details.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(full)!=400*3 or len({(r['query_id'],r['method']) for r in full})!=1200:raise ValueError('Need completed v2 baseline for all methods')
    current={(r['query_id'],r['method']):r for r in full}
    fields=['query','collection','split','domain','style','k','metrics','known_positives','forbidden_leaks','returned','control','candidates']
    for old in before:
        new=current[(old['query_id'],old['method'])]
        if any(old[key]!=new[key] for key in fields):raise AssertionError('Frozen v1 ranking changed: '+old['query_id']+'/'+old['method'])
    out=ROOT/'results/offline-sample'
    with patch('models.request_json',side_effect=AssertionError('Offline sample attempted provider request')) as provider:
        run(argparse.Namespace(dataset=None,output=str(out),split='all',bm25_only=False,embed_missing=False,query_ids=','.join(IDS)))
    sample=[json.loads(line) for line in (out/'details.jsonl').read_text(encoding='utf-8').splitlines()]
    if len(sample)!=len(IDS)*3:raise AssertionError('Sample incomplete')
    for row in sample:
        if row!=current[(row['query_id'],row['method'])]:raise AssertionError('Cached sample ranking mismatch')
    assert provider.call_count==0
    proof=dict(version=manifest['version'],dataset_sha256=manifest['dataset_sha256'],corpus_sha256=manifest['corpus_sha256'],
        full_baseline_queries=400,full_baseline_method_query_results=1200,
        frozen_v1_queries=80,frozen_v1_method_query_results_identical=len(before),
        offline_sample_queries=IDS,offline_sample_method_query_results_identical=len(sample),provider_requests=provider.call_count,
        scope='全量400题完成一次基线；冻结v1的80题三种方法逐题一致；仅对明列的16题做独立离线重放，不声称400题全部重放。')
    for name in ('expansion-regression.json','reproducibility.json'):
        (ROOT/'results'/name).write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS: 400-query baseline; frozen 80-query parity; 16-query offline replay; zero provider requests')

if __name__=='__main__':main()
