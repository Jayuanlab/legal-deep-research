import unittest
from unittest.mock import patch
import models
from vectors import content_hash


class ModelTests(unittest.TestCase):
    def test_aliyun_uses_its_own_credential_and_preserves_text_profile(self):
        env={'LEGAL_EMBEDDING_PROVIDER':'aliyun','DASHSCOPE_API_KEY':'ali-secret','OPENAI_EMBEDDINGS_API_KEY':'jina-secret',
            'LLM_EMBEDDING_BASE_URL':'https://api.jina.ai/v1','LLM_EMBEDDING_MODEL':'jina-embeddings-v3',
            'INTERACTION_PROCESSOR_LLM_API_KEY':'text-secret','INTERACTION_PROCESSOR_LLM_MODEL':'qwen3.7-plus'}
        with patch.object(models,'environment',return_value=env):
            text,embedding=models.config()
        self.assertEqual(embedding['key'],'ali-secret')
        self.assertEqual(embedding['model'],'text-embedding-v4')
        self.assertEqual(embedding['dimensions'],1024)
        self.assertEqual(embedding['base'],'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.assertEqual(text['key'],'text-secret')

    def test_aliyun_never_substitutes_jina_key_when_credential_missing(self):
        with patch.object(models,'environment',return_value={'LEGAL_EMBEDDING_PROVIDER':'aliyun','OPENAI_EMBEDDINGS_API_KEY':'jina-secret'}):
            cfg=models.config()[1]
        self.assertEqual(cfg['key'],'')
        with self.assertRaises(models.ModelError):models.require(cfg)

    def test_equal_dimensions_do_not_make_embedding_spaces_compatible(self):
        one=dict(base='https://api.jina.ai/v1',model='jina-embeddings-v3',dimensions=1024,protocol='openai')
        two=dict(base='https://dashscope.aliyuncs.com/compatible-mode/v1',model='text-embedding-v4',dimensions=1024,protocol='openai')
        self.assertNotEqual(models.embedding_identity(one),models.embedding_identity(two))

    def test_aliyun_payload_has_no_jina_only_fields(self):
        cfg=dict(key='ali-secret',base='https://dashscope.aliyuncs.com/compatible-mode/v1',model='text-embedding-v4',dimensions=2,protocol='openai')
        with patch.object(models,'config',return_value=({},cfg)),patch.object(models,'request_json',return_value={'data':[dict(index=0,embedding=[3,4])]}) as request:
            self.assertEqual(models.embed(['test'],query=True),[[.6,.8]])
        self.assertNotIn('task',request.call_args.args[2]);self.assertNotIn('normalized',request.call_args.args[2])

    def test_zhiyu_endpoint_migration(self):
        env={'INTERACTION_PROCESSOR_LLM_API_KEY':'secret','INTERACTION_PROCESSOR_LLM_BASE_URL':'https://opencode.ai/zen/go',
             'INTERACTION_PROCESSOR_LLM_MODEL':'qwen3.7-plus','INTERACTION_PROCESSOR_LLM_PROVIDER':'anthropic_compatible'}
        with patch.object(models,'environment',return_value=env):
            text,_=models.config()
            self.assertEqual(text['base'],'https://opencode.ai/inference/go/anthropic')
            self.assertEqual(text['protocol'],'anthropic_compatible')

    def test_embedding_response_order_and_normalization(self):
        cfg={'key':'test','base':'https://api.jina.ai/v1','model':'test','dimensions':2,'protocol':'openai'}
        response={'data':[{'index':1,'embedding':[0,5]},{'index':0,'embedding':[3,4]}]}
        with patch.object(models,'config',return_value=({},cfg)),patch.object(models,'request_json',return_value=response) as request:
            self.assertEqual(models.embed(['a','b']),[[0.6,0.8],[0.0,1.0]])
            self.assertEqual(request.call_args.args[2]['task'],'retrieval.passage')

    def test_query_task(self):
        cfg={'key':'test','base':'https://api.jina.ai/v1','model':'test','dimensions':2,'protocol':'openai'}
        with patch.object(models,'config',return_value=({},cfg)),patch.object(models,'request_json',return_value={'data':[{'index':0,'embedding':[1,1]}]}) as request:
            models.embed(['q'],query=True)
            self.assertEqual(request.call_args.args[2]['task'],'retrieval.query')

    def test_invalid_embedding_rejected(self):
        cfg={'key':'test','base':'https://example.com','model':'test','dimensions':2,'protocol':'openai'}
        with patch.object(models,'config',return_value=({},cfg)),patch.object(models,'request_json',return_value={'data':[{'index':0,'embedding':[0,0]}]}):
            with self.assertRaises(models.ModelError): models.embed(['a'])

    def test_truncated_completion_rejected(self):
        cfg={'key':'test','base':'https://example.com','model':'test','protocol':'anthropic_compatible'}
        with patch.object(models,'config',return_value=(cfg,{})),patch.object(models,'request_json',return_value={'stop_reason':'max_tokens'}):
            with self.assertRaises(models.ModelError): models.complete('system','prompt')

    def test_public_status_has_no_credentials(self):
        cfg={'key':'secret','base':'https://example.com','model':'test','protocol':'openai','dimensions':2}
        with patch.object(models,'config',return_value=(cfg,cfg)):
            self.assertNotIn('secret',str(models.public_config()))

    def test_changed_text_invalidates_cache(self):
        self.assertNotEqual(content_hash({'title':'a','text':'b'}),content_hash({'title':'a','text':'c'}))


if __name__=='__main__': unittest.main()
