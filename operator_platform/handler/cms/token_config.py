# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.error import ParamsError
from operator_platform.service.token_config import TokenConfigService

__all__ = [
    'TokenConfigHandler',
    'TokenConfigOptionsHandler',
    'TokenConfigChannelsHandler',
    'TokenConfigTestHandler',
]


class TokenConfigChannelsHandler(BaseHandler):

    async def get(self):
        self.require_admin()
        result = await TokenConfigService.get_channels()
        self.render({'channelList': result})


class TokenConfigOptionsHandler(BaseHandler):

    async def get(self):
        self.require_admin()
        result = await TokenConfigService.get_options()
        self.render({'tokenConfigList': result})


class TokenConfigTestHandler(BaseHandler):

    async def post(self, token_id=None):
        if not token_id:
            raise ParamsError
        self.require_admin()
        result = await TokenConfigService.test_token(token_id)
        self.render(result)


class TokenConfigHandler(BaseHandler):

    async def get(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        result = await TokenConfigService.get_tokens()
        self.render({'tokenConfigList': result})

    async def post(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('name', str, True)
        self.add_json_argument('channel', str, True)
        self.add_json_argument('credentials', dict, True)
        self.add_json_argument('enabled', bool, False)
        result = await TokenConfigService.create_token(
            name=self.json.name,
            channel=self.json.channel,
            credentials=self.json.credentials,
            enabled=getattr(self.json, 'enabled', True),
        )
        self.render(result)

    async def put(self, token_id=None):
        if not token_id:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('name', str, False)
        self.add_json_argument('credentials', dict, False)
        self.add_json_argument('enabled', bool, False)
        kwargs = {}
        if hasattr(self.json, 'name') and self.json.name is not None:
            kwargs['name'] = self.json.name
        if hasattr(self.json, 'credentials') and self.json.credentials is not None:
            kwargs['credentials'] = self.json.credentials
        if hasattr(self.json, 'enabled') and self.json.enabled is not None:
            kwargs['enabled'] = self.json.enabled
        result = await TokenConfigService.update_token(token_id, **kwargs)
        self.render(result)

    async def delete(self, token_id=None):
        if not token_id:
            raise ParamsError
        self.require_admin()
        await TokenConfigService.delete_token(token_id)
        self.render()
