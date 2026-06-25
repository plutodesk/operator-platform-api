# -*- coding: utf-8 -*-

import unittest

from tornado.web import HTTPError

from operator_platform.handler.cms.base import BaseHandler


class FakeAdminHandler(BaseHandler):
    def __init__(self, user):
        self.current_user = user

    def get(self):
        self.require_admin()


class AdminAuthTest(unittest.TestCase):

    def test_non_admin_raises_403(self):
        handler = FakeAdminHandler({'user_id': 'u1', 'role': 'user'})
        with self.assertRaises(HTTPError) as ctx:
            handler.require_admin()
        self.assertEqual(ctx.exception.status_code, 403)

    def test_admin_passes(self):
        handler = FakeAdminHandler({'user_id': 'u1', 'role': 'admin'})
        handler.require_admin()

    def test_missing_role_defaults_user(self):
        handler = FakeAdminHandler({'user_id': 'u1'})
        with self.assertRaises(HTTPError) as ctx:
            handler.require_admin()
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == '__main__':
    unittest.main()
