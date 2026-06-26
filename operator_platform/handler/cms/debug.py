# -*- encoding: utf-8 -*-
#
# @Date: 2026

from tornado.web import HTTPError

from seal.conf import options

from operator_platform.handler.cms.base import UACHandler
from operator_platform.service import UserService
from operator_platform.service.cdn import effective_cdn_url

__all__ = ['DebugLoginHandler', 'DebugUsersHandler']


class _LocalOnlyMixin(object):

    def prepare(self):
        if not options.LOCAL:
            raise HTTPError(404)
        return super().prepare()


class DebugLoginHandler(_LocalOnlyMixin, UACHandler):

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", self.request.headers.get('Origin', '*'))
        self.set_header("Access-Control-Allow-Credentials", 'true')
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Content-Type, Authorization")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish(None)

    async def post(self):
        self.add_json_argument('email', str, True)
        email = self.json.email.strip().lower()
        user = await UserService.login_by_email(email)
        user = self.login(user)
        user['cdn_url'] = effective_cdn_url()
        user['local'] = True
        self.render(user)


class DebugUsersHandler(_LocalOnlyMixin, UACHandler):

    def set_default_headers(self):
        DebugLoginHandler.set_default_headers(self)

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish(None)

    async def get(self):
        user_list = await UserService.list_active_users()
        self.render({'userList': user_list})
