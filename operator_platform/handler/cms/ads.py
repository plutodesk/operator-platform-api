# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.service.ads import AdsService

__all__ = [
    'AdsPublishHandler',
    'AdsPublishOptionsHandler',
]


class AdsPublishOptionsHandler(BaseHandler):

    async def get(self):
        self.add_query_argument('product', str, False)
        result = await AdsService.get_publish_options(
            product=getattr(self.query, 'product', None),
        )
        self.render({'publishOptionList': result})


class AdsPublishHandler(BaseHandler):

    async def post(self):
        self.add_json_argument('material_id', str, True)
        self.add_json_argument('version', int, True)
        self.add_json_argument('channel', str, True)
        self.add_json_argument('platform_config_id', str, False)
        self.add_json_argument('language', str, False)
        self.add_json_argument('size', str, False)
        self.add_json_argument('upload_paths', list, False)
        result = await AdsService.publish_stub(
            material_id=self.json.material_id,
            version=self.json.version,
            channel=self.json.channel,
            operator_id=self.current_user['id'],
            platform_config_id=getattr(self.json, 'platform_config_id', None),
            language=self.json.language,
            size=self.json.size,
            upload_paths=getattr(self.json, 'upload_paths', None),
        )
        self.render(result)
