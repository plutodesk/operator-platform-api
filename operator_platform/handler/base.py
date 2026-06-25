# -*- encoding: utf-8 -*-
#
# @Date: 2026

from seal.web.handler import APIHandler
from tornado.web import HTTPError


class BaseHandler(APIHandler):

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", self.request.headers.get('Origin', '*'))
        self.set_header("Access-Control-Allow-Credentials", 'true')
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Content-Type, Authorization")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish(None)

    @property
    def package_name(self):
        return self.request.headers.get('packageName')

    @property
    def platform(self):
        return self.request.headers.get('platform', 'android').lower()

    @property
    def app_version(self):
        return self.request.headers.get('appVersion', '1.0.0')

    @classmethod
    def get_version_number(cls, version):
        """把 a.b.c 版本号转成可比较的定长字符串(每段 3 位)。"""
        num_list = version.split('.')
        if len(num_list) > 3:
            raise HTTPError(400, 'App Version Error')
        for num in num_list:
            if len(num) > 3:
                raise HTTPError(400, 'App Version Error')
        try:
            num_list = [int(num or 0) for num in num_list]
        except ValueError:
            raise HTTPError(400, 'App Version Error')
        for _ in range(3 - len(num_list)):
            num_list.append(0)
        return '%03d%03d%03d' % tuple(num_list)

    @property
    def language(self):
        return self.request.headers.get('language', 'EN')

    @property
    def country(self):
        return self.request.headers.get('country')

    @property
    def timezone(self):
        return self.request.headers.get('timezone', 'UTC')

    @property
    def debug(self):
        return self.request.headers.get('mode') == 'debug'

    @property
    def day(self):
        return int(self.request.headers.get('day', 0))

    @property
    def user_id(self):
        return self.request.headers.get('userId', '')
