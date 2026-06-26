# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.service.ads import AdsService

__all__ = [
    'AdsPublishHandler',
]


class AdsPublishHandler(BaseHandler):

    async def post(self):
        self.add_json_argument('material_id', str, True)
        self.add_json_argument('version', int, True)
        self.add_json_argument('channel', str, True)
        self.add_json_argument('language', str, False)
        self.add_json_argument('size', str, False)
        result = await AdsService.publish_stub(
            material_id=self.json.material_id,
            version=self.json.version,
            channel=self.json.channel,
            operator_id=self.current_user['id'],
            language=self.json.language,
            size=self.json.size,
        )
        self.render(result)
