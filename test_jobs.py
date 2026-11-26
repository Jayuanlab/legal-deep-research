import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import corpus
import research_jobs as jobs
from models import ModelError


class JobTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        p=patch.object(corpus,'DB',Path(folder.name)/'test.sqlite3');p.start();self.addCleanup(p.stop)
        jobs.setup()

    def test_admission_control(self):
        with patch.object(jobs.EXECUTOR,'submit'):
            first=jobs.start_job('合同解除');jobs.start_job('违约金')
            with self.assertRaises(ModelError):jobs.start_job('第三项')
        self.assertEqual(jobs.get_job(first['id'])['status'],'queued')

    def test_cancel_flag_persists_through_progress(self):
        with patch.object(jobs.EXECUTOR,'submit'):job=jobs.start_job('合同')
        jobs.cancel_job(job['id']);jobs.save(job['id'],dict(question='合同',events=[]),'running')
        self.assertTrue(jobs.cancelled(job['id']))

    def test_cancel_during_completion_does_not_publish_result(self):
        with patch.object(jobs.EXECUTOR,'submit'):job=jobs.start_job('合同')
        jobs.cancel_job(job['id']);jobs.save(job['id'],dict(question='合同',result={'report':'result'}),'completed')
        stored=jobs.get_job(job['id']);self.assertEqual(stored['status'],'cancelled');self.assertNotIn('result',stored)

    def test_model_error_preserves_events(self):
        with patch.object(jobs.EXECUTOR,'submit'):job=jobs.start_job('合同')
        def fail(question,emit,cancelled):
            emit(dict(stage='检索',detail='已有证据'))
            raise ModelError('模型服务失败')
        with patch.object(jobs,'research',side_effect=fail):jobs.run(job['id'],'合同')
        stored=jobs.get_job(job['id']);self.assertEqual(stored['status'],'failed');self.assertEqual(len(stored['events']),1)

    def test_restart_marks_unfinished_interrupted(self):
        with patch.object(jobs.EXECUTOR,'submit'):job=jobs.start_job('合同')
        jobs.setup();self.assertEqual(jobs.get_job(job['id'])['status'],'interrupted')


if __name__=='__main__':unittest.main()
