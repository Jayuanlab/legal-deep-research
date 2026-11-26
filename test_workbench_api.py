import base64,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
import corpus,matter_store,server,research_jobs

class WorkbenchApiTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();p=Path(self.tmp.name)
  self.db=patch.object(corpus,'DB',p/'test.sqlite3');self.db.start()
  self.store=patch.object(matter_store,'STORE',p/'files');self.store.start()
  self.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
  self.url='http://127.0.0.1:'+str(self.http.server_port)
 def tearDown(self):
  self.http.shutdown();self.thread.join();self.http.server_close();self.store.stop();self.db.stop();self.tmp.cleanup()
 def request(self,path,body=None):
  req=urllib.request.Request(self.url+path,data=json.dumps(body,ensure_ascii=False).encode() if body is not None else None,headers={'Content-Type':'application/json','Origin':self.url})
  with urllib.request.urlopen(req) as r:return json.load(r)
 def test_upload_and_selected_snapshot_enter_research_job(self):
  case=self.request('/api/matters',dict(name='合成API验证',goal='performance',client_role='buyer'))
  d=self.request('/api/matters/'+case['id']+'/documents',dict(name='合同.txt',kind='contract',content_base64=base64.b64encode('交付日期为2026-10-01。'.encode()).decode()))
  with patch.object(server,'start_job',return_value=dict(id='test',status='queued')) as start:
   self.request('/api/research/jobs',dict(question='供应商逾期交付设备怎么办',matter_id=case['id'],material_ids=[d['id']],client_profile=dict(goal='settlement',client_role='buyer')))
  args=start.call_args.args;self.assertEqual(args[1]['documents'][0]['id'],d['id']);self.assertEqual(args[1]['goal'],'settlement');self.assertEqual(args[2]['goal'],'settlement')
  self.assertEqual(self.request('/api/matters/'+case['id'])['name'],'合成API验证')
  self.assertEqual(self.request('/api/matters')['items'][0]['id'],case['id'])
 def test_cross_case_selection_never_starts_model(self):
  m=self.request('/api/matters',dict(name='测试'))
  with patch.object(server,'start_job') as start:
   with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/api/research/jobs',dict(question='设备交付争议',matter_id=m['id'],material_ids=['other']))
   self.assertEqual(caught.exception.code,400);caught.exception.close()
   start.assert_not_called()
 def test_job_preserves_case_snapshot(self):
  research_jobs.setup();context=dict(id='test',name='合成案',documents=[])
  with patch.object(research_jobs.EXECUTOR,'submit'):job=research_jobs.start_job('设备交付争议',context,dict(goal='performance'))
  def research(question,emit,cancelled,case_context,client_goal):
   self.assertEqual(case_context,context);self.assertEqual(client_goal['goal'],'performance');return dict(report='fixture',events=[])
  with patch.object(research_jobs,'research',side_effect=research):research_jobs.run(job['id'],'设备交付争议',context,dict(goal='performance'))
  stored=research_jobs.get_job(job['id']);self.assertEqual(stored['status'],'completed');self.assertEqual(stored['case_snapshot'],context)

if __name__=='__main__':unittest.main()
