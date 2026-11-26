import json,unittest
from unittest.mock import patch
from research_engine import Budget

class ReportTimeoutTests(unittest.TestCase):
 def test_long_report_request_can_wait_longer_than_legacy_short_answer(self):
  with patch('research_engine.complete',return_value=('{}','fixture')) as complete:
   Budget().ask('结构化长报告',{},6500)
  self.assertGreaterEqual(complete.call_args.kwargs['timeout'],180)
  self.assertLessEqual(complete.call_args.kwargs['timeout'],240)
 def test_short_stage_keeps_legacy_cap(self):
  with patch('research_engine.complete',return_value=('{}','fixture')) as complete:
   Budget().ask('拆题',{},1200)
  self.assertLessEqual(complete.call_args.kwargs['timeout'],120)
 def test_long_request_does_not_exceed_total_remaining_budget(self):
  with patch('research_engine.time.monotonic',return_value=590),patch('research_engine.complete',return_value=('{}','fixture')) as complete:
   Budget(started=0,seconds=600).ask('结构化长报告',{},6500)
  self.assertLessEqual(complete.call_args.kwargs['timeout'],10)
if __name__=='__main__':unittest.main()
