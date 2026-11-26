import io
import json
import unittest
import urllib.error
import ssl
from unittest.mock import patch,MagicMock
import models

class ModelTransportTests(unittest.TestCase):
    def test_temporary_connection_reset_retries_within_budget(self):
        response=MagicMock();response.__enter__.return_value=io.BytesIO(b'{"ok":true}')
        opener=MagicMock();opener.open.side_effect=[urllib.error.URLError(ConnectionResetError()),response]
        with patch.object(models.urllib.request,'build_opener',return_value=opener),patch.object(models.time,'sleep'):
            self.assertEqual(models.request_json('https://example.com','fake',{},timeout=10),{'ok':True})
        self.assertEqual(opener.open.call_count,2)

    def test_non_json_has_specific_safe_error(self):
        response=MagicMock();response.__enter__.return_value=io.BytesIO(b'<html>gateway failure</html>')
        opener=MagicMock();opener.open.return_value=response
        with patch.object(models.urllib.request,'build_opener',return_value=opener),patch.object(models.time,'sleep'):
            with self.assertRaises(models.ModelError) as error:models.request_json('https://example.com','secret',{},timeout=10)
        self.assertIn('JSON',str(error.exception))
        self.assertNotIn('连接失败',str(error.exception))
        self.assertNotIn('secret',str(error.exception))

    def test_tls_error_retains_category_and_attempt_count(self):
        opener=MagicMock();opener.open.side_effect=urllib.error.URLError(ssl.SSLEOFError())
        with patch.object(models.urllib.request,'build_opener',return_value=opener),patch.object(models.time,'sleep'):
            with self.assertRaises(models.ModelServiceError) as error:models.request_json('https://example.com','secret',{},timeout=10,service='embedding')
        self.assertEqual((error.exception.code,error.exception.service,error.exception.attempts),('tls','embedding',3))
        self.assertTrue(error.exception.retryable)

    def test_certificate_and_unauthorized_errors_not_retried(self):
        for fault in [urllib.error.URLError(ssl.SSLCertVerificationError()),urllib.error.HTTPError('https://example.com',401,'unauthorized',{},None)]:
            opener=MagicMock();opener.open.side_effect=fault
            with patch.object(models.urllib.request,'build_opener',return_value=opener),patch.object(models.time,'sleep'):
                with self.assertRaises(models.ModelServiceError) as error:models.request_json('https://example.com','secret',{},timeout=10)
            self.assertFalse(error.exception.retryable)
            self.assertEqual(opener.open.call_count,1)

    def test_retry_does_not_exceed_remaining_budget(self):
        opener=MagicMock();opener.open.side_effect=urllib.error.URLError(TimeoutError())
        with patch.object(models.urllib.request,'build_opener',return_value=opener),patch.object(models.time,'sleep') as sleep:
            with self.assertRaises(models.ModelServiceError):models.request_json('https://example.com','secret',{},timeout=.1)
        self.assertEqual(opener.open.call_count,1);sleep.assert_not_called()

if __name__=='__main__':unittest.main()
