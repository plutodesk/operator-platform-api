# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.error import ParamsError
from operator_platform.service.ad_platform_config import AdPlatformConfigService

__all__ = [
    'AdPlatformConfigHandler',
]


class AdPlatformConfigHandler(BaseHandler):

    async def get(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        result = await AdPlatformConfigService.get_configs()
        self.render({'adPlatformConfigList': result})

    async def post(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('name', str, True)
        self.add_json_argument('channel', str, True)
        self.add_json_argument('product', str, False)
        self.add_json_argument('token_config_id', str, True)
        self.add_json_argument('settings', dict, True)
        self.add_json_argument('enabled', bool, False)
        result = await AdPlatformConfigService.create_config(
            name=self.json.name,
            channel=self.json.channel,
            product=getattr(self.json, 'product', '') or '',
            token_config_id=self.json.token_config_id,
            settings=self.json.settings,
            enabled=getattr(self.json, 'enabled', True),
        )
        self.render(result)

    async def put(self, config_id=None):
        if not config_id:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('name', str, False)
        self.add_json_argument('product', str, False)
        self.add_json_argument('token_config_id', str, False)
        self.add_json_argument('settings', dict, False)
        self.add_json_argument('enabled', bool, False)
        kwargs = {}
        if hasattr(self.json, 'name') and self.json.name is not None:
            kwargs['name'] = self.json.name
        if hasattr(self.json, 'product') and self.json.product is not None:
            kwargs['product'] = self.json.product
        if hasattr(self.json, 'token_config_id') and self.json.token_config_id is not None:
            kwargs['token_config_id'] = self.json.token_config_id
        if hasattr(self.json, 'settings') and self.json.settings is not None:
            kwargs['settings'] = self.json.settings
        if hasattr(self.json, 'enabled') and self.json.enabled is not None:
            kwargs['enabled'] = self.json.enabled
        result = await AdPlatformConfigService.update_config(config_id, **kwargs)
        self.render(result)

    async def delete(self, config_id=None):
        if not config_id:
            raise ParamsError
        self.require_admin()
        await AdPlatformConfigService.delete_config(config_id)
        self.render()
