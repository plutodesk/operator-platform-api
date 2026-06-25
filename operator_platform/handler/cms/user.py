# -*- encoding: utf-8 -*-
#
# @Date: 2026

from seal.conf import options
from google.oauth2 import id_token
from google.auth.transport import requests

from operator_platform.handler.cms.base import UACHandler
from operator_platform.service import UserService
from operator_platform.error import ParamsError

__all__ = [
    'OAuth2LoginHandler',
]


class OAuth2LoginHandler(UACHandler):

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", self.request.headers.get('Origin', '*'))
        self.set_header("Access-Control-Allow-Credentials", 'true')
        self.set_header("Access-Control-Allow-Headers", "x-requested-with, Content-Type, Authorization")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, PUT, DELETE')

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish(None)

    async def post(self):
        self.add_json_argument('platform', str, True)
        if self.json.platform == 'google':
            if options.LOCAL:
                user = self.debug_user
            else:
                self.add_json_argument('id_token', str, True)
                info = id_token.verify_oauth2_token(
                    self.json.id_token, requests.Request(), options.OAUTH_CLIENT_ID
                )
                domain = options.OAUTH_EMAIL_DOMAIN
                if domain and not info['email'].endswith(domain):
                    raise ParamsError
                user = {
                    'user_id': info['sub'],
                    'name': info['name'],
                    'email': info['email'],
                    'avatar': info.get('picture', ''),
                }
            user = await UserService.login(user)
            user = self.login(user)
        else:
            raise ParamsError
        self.render(user)
