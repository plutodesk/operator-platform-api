# -*- coding: utf-8 -*-

import json
import unittest

from tornado.web import HTTPError

from operator_platform.error import ParamsError
from operator_platform.handler.base import BaseHandler as ClientBaseHandler
from operator_platform.handler.cms.base import UACHandler
from operator_platform.service import category as category_module
from operator_platform.service.category import CategoryService


class FakeCookieHandler(UACHandler):
    def __init__(self, cookie):
        self.cookie = cookie

    def get_secure_cookie(self, key):
        return self.cookie


class StabilityTest(unittest.TestCase):

    def test_invalid_category_id_raises_params_error(self):
        with self.assertRaises(ParamsError):
            CategoryService._object_id('not-an-object-id')

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


class MissingCategory:

    @classmethod
    async def find_one_and_update(cls, spec, update, return_document=False):
        return None

    @classmethod
    async def find_one_and_delete(cls, spec):
        return None


class CategoryMutationTest(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.original_category = category_module.Category
        category_module.Category = MissingCategory

    async def asyncTearDown(self):
        category_module.Category = self.original_category

    async def test_update_missing_category_raises_params_error(self):
        with self.assertRaises(ParamsError):
            await CategoryService.update_category(
                '000000000000000000000001',
                {'EN': 'Name'},
                '',
                [],
                [],
                True,
            )

    async def test_delete_missing_category_raises_params_error(self):
        with self.assertRaises(ParamsError):
            await CategoryService.delete_category('000000000000000000000001')


if __name__ == '__main__':
    unittest.main()
