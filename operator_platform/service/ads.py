# -*- encoding: utf-8 -*-
#
# @Date: 2026

from seal.utils.tools import time10

from operator_platform.constants.material_meta import CHANNELS
from operator_platform.db import Material
from operator_platform.error import ParamsError
from operator_platform.service.material import MaterialService

__all__ = ['AdsService']


class AdsService(object):

    @classmethod
    async def publish_stub(cls, material_id, version, channel, operator_id, language=None, size=None):
        if channel not in CHANNELS:
            raise ParamsError
        existing = await Material.find_one({'_id': MaterialService._object_id(material_id)})
        if not existing or existing.production_status != 'completed':
            raise ParamsError
        if existing.version != version:
            return {
                'api_status': 'stub',
                'material': None,
                'conflict': {
                    'id': material_id,
                    'message': '数据已被他人更新',
                    'serverMaterial': existing.info,
                },
            }
        usage = dict(existing.channel_usage or {})
        usage[channel] = True
        existing.channel_usage = usage
        operators = list(existing.ads_operator_ids or [])
        if operator_id and operator_id not in operators:
            operators.append(operator_id)
        existing.ads_operator_ids = operators
        if language:
            existing.language = language
        if size:
            existing.size = size
        existing.version = existing.version + 1
        existing.u_time = time10()
        await existing.save()
        return {'api_status': 'stub', 'material': existing.info, 'conflict': None}
