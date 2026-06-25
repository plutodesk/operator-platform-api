# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.error import ParamsError
from operator_platform.service.user import UserService

__all__ = [
    'AdminUserHandler',
    'UserOptionsHandler',
]


class UserOptionsHandler(BaseHandler):

    async def get(self):
        result = await UserService.get_user_options()
        self.render({'userList': result})


class AdminUserHandler(BaseHandler):

    async def get(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        result = await UserService.get_users()
        self.render({'userList': result})

    async def post(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('email', str, True)
        self.add_json_argument('name', str, True)
        self.add_json_argument('role', str, False)
        result = await UserService.create_user(
            email=self.json.email,
            name=self.json.name,
            role=getattr(self.json, 'role', None) or 'user',
        )
        self.render(result)

    async def put(self, user_id=None):
        if not user_id:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('role', str, False)
        self.add_json_argument('active', bool, False)
        kwargs = {}
        if hasattr(self.json, 'role') and self.json.role is not None:
            kwargs['role'] = self.json.role
        if hasattr(self.json, 'active') and self.json.active is not None:
            kwargs['active'] = self.json.active
        result = await UserService.update_user(user_id, **kwargs)
        self.render(result)
