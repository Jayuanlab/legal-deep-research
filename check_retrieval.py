"""Focused real embedding smoke; no text generation or web search."""
import json
from corpus import connection
from vectors import retrieve, status

assert status()['ready'], status()
with connection() as db:
    originals={key:json.loads(raw) for key,raw in db.execute('SELECT id,payload FROM documents')}
for question in ['劳动合同违法解除，经济补偿和赔偿金如何计算？','合同约定的违约金过高，法院如何调整？']:
    hits=retrieve(question)
    assert hits and any(d['doc_type']=='law' for d in hits)
    if '劳动' in question:
        assert any('劳动' in d.get('law_name','') for d in hits), [d['title'] for d in hits]
    for doc in hits:
        source=originals[doc['parent_id']];span=doc['fragment']
        assert source['text'][span['start']:span['end']]==doc['text']
        assert doc.get('reference_status')!='not_reference'
    print(json.dumps(dict(question=question,hits=[dict(id=d['id'],title=d['title'],chars=len(d['text'])) for d in hits]),ensure_ascii=False))
print('PASS: real embeddings, labor/contract retrieval, exact source spans, withdrawn exclusion')
