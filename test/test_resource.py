# test/test_resource.py
import hashlib
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

import operator_platform  # noqa: F401 — load define('BUCKET')

from operator_platform.service.resource import ResourceService

class ResourceServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_upload_builds_md5_filename(self):
        upload_file = {
            'filename': 'demo.mp4',
            'body': b'hello',
            'content_type': 'video/mp4',
        }
        mock_bucket = MagicMock()
        mock_bucket.put_blob_from_bytes = AsyncMock(return_value=None)
        with patch('operator_platform.service.resource.GCSBucket', return_value=mock_bucket):
            with patch('operator_platform.service.resource.options', MagicMock()) as opts:
                opts.BUCKET = 'test-bucket'
                name = await ResourceService.upload_resource('ads/material', upload_file)
        expected = f'ads/material/{hashlib.md5(b"hello").hexdigest()}.mp4'
        self.assertEqual(name, expected)
        mock_bucket.put_blob_from_bytes.assert_awaited_once()
