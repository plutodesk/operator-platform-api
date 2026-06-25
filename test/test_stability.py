# -*- coding: utf-8 -*-

import json
import unittest

from tornado.web import HTTPError

from operator_platform.handler.base import BaseHandler as ClientBaseHandler
from operator_platform.handler.cms.base import UACHandler


class FakeCookieHandler(UACHandler):
    def __init__(self, cookie):
        self.cookie = cookie

    def get_secure_cookie(self, key):
        return self.cookie


class StabilityTest(unittest.TestCase):

    def test_version_with_non_numeric_segment_returns_http_400(self):
        with self.assertRaises(HTTPError) as ctx:
            ClientBaseHandler.get_version_number('1.ab.0')
        self.assertEqual(ctx.exception.status_code, 400)

    def test_broken_user_cookie_is_treated_as_missing_user(self):
        handler = FakeCookieHandler(b'{broken-json')
        self.assertIsNone(handler.get_current_user())

    def test_valid_user_cookie_still_decodes(self):
        user = {'user_id': 'u1', 'name': 'A'}
        handler = FakeCookieHandler(json.dumps(user).encode('utf-8'))
        self.assertEqual(handler.get_current_user(), user)


if __name__ == '__main__':
    unittest.main()
