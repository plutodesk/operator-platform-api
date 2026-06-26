# test/test_cdn.py
import unittest
from unittest.mock import MagicMock, patch

import operator_platform  # noqa: F401

from operator_platform.service.cdn import effective_cdn_url, use_local_upload


class CdnConfigTest(unittest.TestCase):
    def test_use_local_upload_respects_explicit_local_upload(self):
        with patch('operator_platform.service.cdn.options', MagicMock()) as opts:
            opts.LOCAL_UPLOAD = True
            opts.LOCAL = False
            self.assertTrue(use_local_upload())
            opts.LOCAL_UPLOAD = False
            self.assertFalse(use_local_upload())

    def test_use_local_upload_defaults_to_local(self):
        with patch('operator_platform.service.cdn.options', MagicMock()) as opts:
            opts.LOCAL_UPLOAD = None
            opts.LOCAL = True
            self.assertTrue(use_local_upload())
            opts.LOCAL = False
            self.assertFalse(use_local_upload())

    def test_effective_cdn_url_uses_local_base_in_debug(self):
        with patch('operator_platform.service.cdn.options', MagicMock()) as opts:
            opts.DEBUG = True
            opts.PORT = 20010
            opts.LOCAL_UPLOAD = None
            opts.LOCAL = False
            opts.CDN_URL = 'https://example.com/'
            self.assertEqual(
                effective_cdn_url(),
                'http://127.0.0.1:20010/static/uploads/',
            )

    def test_effective_cdn_url_uses_configured_cdn_in_production(self):
        with patch('operator_platform.service.cdn.options', MagicMock()) as opts:
            opts.DEBUG = False
            opts.LOCAL_UPLOAD = None
            opts.LOCAL = False
            opts.CDN_URL = 'https://example.com'
            self.assertEqual(effective_cdn_url(), 'https://example.com/')
