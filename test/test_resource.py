# test/test_resource.py
import hashlib
import os
import shutil
import tempfile
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

import operator_platform  # noqa: F401 — load define('BUCKET')

from google.api_core.exceptions import Forbidden
from operator_platform.error import ParamsError
from operator_platform.service.resource import ResourceService


def mock_options(**kwargs):
    opts = MagicMock()
    opts.BUCKET = kwargs.get('BUCKET', 'test-bucket')
    opts.LOCAL = kwargs.get('LOCAL', False)
    opts.LOCAL_UPLOAD = kwargs.get('LOCAL_UPLOAD', None)
    opts.DEBUG = kwargs.get('DEBUG', False)
    return opts


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
            with patch('operator_platform.service.resource.options', mock_options()):
                name = await ResourceService.upload_resource('ads/material', upload_file)
        expected = f'ads/material/{hashlib.md5(b"hello").hexdigest()}.mp4'
        self.assertEqual(name, expected)
        mock_bucket.put_blob_from_bytes.assert_awaited_once()

    async def test_upload_without_bucket_raises_params_error(self):
        upload_file = {
            'filename': 'demo.mp4',
            'body': b'hello',
            'content_type': 'video/mp4',
        }
        with patch('operator_platform.service.resource.options', mock_options(BUCKET='')):
            with self.assertRaises(ParamsError):
                await ResourceService.upload_resource('ads/material', upload_file)

    async def test_upload_uses_local_storage_when_local_upload_enabled(self):
        upload_file = {
            'filename': 'demo.png',
            'body': b'hello',
            'content_type': 'image/png',
        }
        tmp_dir = tempfile.mkdtemp()
        try:
            with patch('operator_platform.db.local_storage.UPLOAD_ROOT', tmp_dir):
                with patch(
                    'operator_platform.service.resource.options',
                    mock_options(LOCAL_UPLOAD=True),
                ):
                    name = await ResourceService.upload_resource('ads/material', upload_file)
            expected = f'ads/material/{hashlib.md5(b"hello").hexdigest()}.png'
            self.assertEqual(name, expected)
            path = os.path.join(tmp_dir, expected)
            self.assertTrue(os.path.isfile(path))
            with open(path, 'rb') as f:
                self.assertEqual(f.read(), b'hello')
        finally:
            shutil.rmtree(tmp_dir)

    async def test_upload_falls_back_to_local_on_gcs_forbidden_in_debug(self):
        upload_file = {
            'filename': 'demo.png',
            'body': b'hello',
            'content_type': 'image/png',
        }
        tmp_dir = tempfile.mkdtemp()
        mock_bucket = MagicMock()
        mock_bucket.put_blob_from_bytes = AsyncMock(side_effect=Forbidden('denied'))
        try:
            with patch('operator_platform.db.local_storage.UPLOAD_ROOT', tmp_dir):
                with patch('operator_platform.service.resource.GCSBucket', return_value=mock_bucket):
                    with patch('operator_platform.service.resource.options', mock_options(DEBUG=True)):
                        name = await ResourceService.upload_resource('ads/material', upload_file)
            expected = f'ads/material/{hashlib.md5(b"hello").hexdigest()}.png'
            self.assertEqual(name, expected)
            self.assertTrue(os.path.isfile(os.path.join(tmp_dir, expected)))
        finally:
            shutil.rmtree(tmp_dir)
