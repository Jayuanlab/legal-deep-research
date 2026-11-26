"""Verify the cached baseline repeats exactly while all provider requests fail."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.evaluate import run
from evaluation.build_dataset import digest
from models import embedding_identity

root=Path(__file__).parent
before=json.loads((root/'results/summary.json').read_text(encoding='utf-8'))
if before['embedding_identity']!=embedding_identity():raise ValueError('Baseline model differs; select the original profile or use a new result directory')
rankings=(root/'results/details.jsonl').read_text(encoding='utf-8')
with patch('models.request_json',side_effect=AssertionError('Offline replay attempted a provider request')) as provider:
    run(argparse.Namespace(split='all',bm25_only=False,embed_missing=False))
after=json.loads((root/'results/summary.json').read_text(encoding='utf-8'))
assert before['groups']==after['groups'] and before['controls']==after['controls']
assert rankings==(root/'results/details.jsonl').read_text(encoding='utf-8')
assert provider.call_count==0
proof=dict(dataset_sha256=after['dataset']['dataset_sha256'],corpus_sha256=after['dataset']['corpus_sha256'],
           rankings_sha256=digest(rankings),metrics_identical=True,rankings_identical=True,provider_requests=provider.call_count)
(root/'results/reproducibility.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: identical metrics and rankings; zero model/provider requests')
