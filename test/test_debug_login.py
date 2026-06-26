# test/test_debug_login.py
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import operator_platform  # noqa: F401

from operator_platform.handler.cms.debug import DebugLoginHandler, DebugUsersHandler
from operator_platform.error import ParamsError


class DebugLoginHandlerTest(unittest.IsolatedAsyncioTestCase):

    async def test_local_false_returns_404(self):
        request = MagicMock()
        request.headers.get.return_value = '*'
        handler = DebugLoginHandler(MagicMock(), request)
        with patch('operator_platform.handler.cms.debug.options', MagicMock(LOCAL=False)):
            with self.assertRaises(Exception) as ctx:
                handler.prepare()
            self.assertEqual(getattr(ctx.exception, 'status_code', None), 404)

    async def test_unknown_email_raises_params_error(self):
        with patch('operator_platform.handler.cms.debug.UserService.login_by_email', new_callable=AsyncMock) as login:
            login.side_effect = ParamsError
            from operator_platform.service.user import UserService
            with self.assertRaises(ParamsError):
                await UserService.login_by_email('missing@bidderdesk.com')

    async def test_list_active_users_returns_sorted_emails(self):
        u1 = MagicMock(email='alice@bidderdesk.com', name='Alice', role='user')
        u2 = MagicMock(email='bob@bidderdesk.com', name='Bob', role='user')
        with patch('operator_platform.service.user.User.query', new_callable=AsyncMock, return_value=[u1, u2]):
            from operator_platform.service.user import UserService
            rows = await UserService.list_active_users()
        self.assertEqual(rows[0]['email'], 'alice@bidderdesk.com')
        self.assertEqual(rows[1]['email'], 'bob@bidderdesk.com')
