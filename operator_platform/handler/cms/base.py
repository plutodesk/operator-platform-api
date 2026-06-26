# -*- encoding: utf-8 -*-
#
# @Date: 2026

import json
import time

from seal.conf import options
from seal.web.handler import APIHandler
from tornado.web import HTTPError

__all__ = [
    'BaseHandler',
    'MeHandler',
    'LogoutHandler',
    'UACHandler',
    'APIHandler',
]

from operator_platform.service import UserService
from operator_platform.service.cdn import effective_cdn_url


class UACHandler(APIHandler):
    """User Access Control: 基于 secure cookie 的会话。"""
    cookie_user_key = "user_info"

    def get_current_user(self):
        user_cookie = self.get_secure_cookie(UACHandler.cookie_user_key)
        if not user_cookie:
            return None
        try:
            return json.loads(user_cookie)
        except (TypeError, ValueError):
            return None

    @property
    def debug_user(self):
        return {
            "user_id": "000000000000000000000",
            "name": "test",
            "email": "test@example.com",
            "avatar": "",
        }

    def login(self, user):
        self.current_user = user
        self.set_secure_cookie(
            UACHandler.cookie_user_key,
            json.dumps(user),
            expires=time.time() + 12 * 3600,
        )
        return user


class BaseHandler(UACHandler):

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", self.request.headers.get('Origin', '*'))
        self.set_header("Access-Control-Allow-Credentials", 'true')
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Content-Type, Authorization")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')
        self.set_header('Cache-Control', 'no-store')

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish(None)

    def require_admin(self):
        role = (self.current_user or {}).get('role', 'user')
        if role != 'admin':
            raise HTTPError(403, 'Forbidden')

    def prepare(self):
        if not self.current_user:
            self.current_user = self.get_current_user()
        if not self.current_user:
            raise HTTPError(401, 'Not Login')
        return super(BaseHandler, self).prepare()


class MeHandler(BaseHandler):

    async def get(self):
        if options.LOCAL:
            self.current_user = await UserService.login(self.current_user)
            user = self.login(self.current_user)
            user['cdn_url'] = effective_cdn_url()
            user['local'] = True
            self.render(user)
        else:
            user = self.current_user
            if await UserService.is_valid(user):
                user = dict(user)
                user['cdn_url'] = effective_cdn_url()
                self.render(user)
            else:
                raise HTTPError(401, 'Not Login')

    def prepare(self):
        if options.LOCAL:
            cookie_user = self.get_current_user()
            self.current_user = cookie_user or self.debug_user
        return super().prepare()


class LogoutHandler(UACHandler):

    def get(self):
        self.clear_cookie(UACHandler.cookie_user_key)
        self.render()
