# -*- encoding: utf-8 -*-
#
# @Date: 2026

from bson.objectid import ObjectId

from seal.utils.tools import time10

from operator_platform.constants.material_meta import CHANNELS
from operator_platform.db import AdPlatformConfig, Material, TokenConfig
from operator_platform.error import ParamsError
from operator_platform.service.ads_config import AdsConfigResolver
from operator_platform.service.google_ads import GoogleAdsService, GoogleAdsUploadError
from operator_platform.service.unity_ads import UnityAdsService, UnityAdsUploadError
from operator_platform.service.material import MaterialService

__all__ = ['AdsService']

_PUBLISH_CHANNELS = {'google', 'unity'}


class AdsService(object):

    @classmethod
    def _channel_published(cls, material, channel):
        publish = material.platform_publish or {}
        if publish.get(channel):
            return True
        usage = material.channel_usage or {}
        return bool(usage.get(channel))

    @classmethod
    def _validate_platform_config(cls, platform, channel, material_product):
        if platform.channel != channel or not platform.enabled:
            raise ParamsError
        config_product = (platform.product or '').strip()
        material_product = (material_product or '').strip()
        if config_product and config_product != material_product:
            raise ParamsError

    @classmethod
    async def _enabled_token_ids(cls):
        token_list = await TokenConfig.query({'enabled': True}, sort=[('channel', 1), ('c_time', 1)])
        return {token.id: token for token in token_list}

    @classmethod
    async def _token_name_map(cls, token_ids):
        if not token_ids:
            return {}
        object_ids = []
        for token_id in token_ids:
            try:
                object_ids.append(ObjectId(token_id))
            except Exception:
                continue
        if not object_ids:
            return {}
        token_list = await TokenConfig.query({'_id': {'$in': object_ids}})
        return {token.id: token.name for token in token_list}

    @classmethod
    def _filter_configs_for_product(cls, configs, product):
        product = (product or '').strip()
        if product:
            matched = [
                config for config in configs
                if (config.product or '').strip() == product
            ]
            if matched:
                return matched
        return [
            config for config in configs
            if not (config.product or '').strip()
        ]

    @classmethod
    def _config_option(cls, config, token_names):
        return {
            'id': config.id,
            'name': config.name,
            'tokenConfigName': token_names.get(config.token_config_id, ''),
            'product': config.product or '',
        }

    @classmethod
    async def get_publish_options(cls, product=None):
        enabled_tokens = await cls._enabled_token_ids()
        if not enabled_tokens:
            return []
        enabled_channels = sorted({token.channel for token in enabled_tokens.values() if token.channel})
        if not enabled_channels:
            return []
        config_list = await AdPlatformConfig.query(
            {'enabled': True, 'channel': {'$in': enabled_channels}},
            sort=[('channel', 1), ('product', 1), ('c_time', 1)],
        )
        token_names = await cls._token_name_map({cfg.token_config_id for cfg in config_list})
        configs_by_channel = {}
        for config in config_list:
            if config.token_config_id not in enabled_tokens:
                continue
            configs_by_channel.setdefault(config.channel, []).append(config)

        product = (product or '').strip() or None
        publish_option_list = []
        for channel in enabled_channels:
            channel_configs = configs_by_channel.get(channel) or []
            if not channel_configs:
                continue
            if product is not None:
                options = cls._filter_configs_for_product(channel_configs, product)
            else:
                options = channel_configs
            if not options:
                continue
            publish_option_list.append({
                'channel': channel,
                'configs': [
                    cls._config_option(config, token_names)
                    for config in options
                ],
            })
        return publish_option_list

    @classmethod
    async def publish(cls, material_id, version, channel, operator_id,
                      platform_config_id=None, language=None, size=None):
        channel = (channel or '').strip().lower()
        if channel not in CHANNELS:
            raise ParamsError
        if channel in _PUBLISH_CHANNELS and not platform_config_id:
            raise ParamsError

        existing = await Material.find_one({'_id': MaterialService._object_id(material_id)})
        if not existing or existing.production_status != 'completed':
            raise ParamsError
        if existing.version != version:
            return {
                'api_status': 'conflict',
                'material': None,
                'conflict': {
                    'id': material_id,
                    'message': '数据已被他人更新，请刷新后再编辑',
                    'serverMaterial': existing.info,
                },
                'google_ads': None,
                'unity': None,
            }
        if cls._channel_published(existing, channel):
            raise ParamsError

        platform = None
        upload_cfg = None
        if channel in _PUBLISH_CHANNELS:
            platform, upload_cfg = await AdsConfigResolver.resolve_by_config_id(platform_config_id)
            cls._validate_platform_config(platform, channel, existing.product)

        google_ads = None
        unity = None
        if channel == 'google':
            try:
                google_ads = await GoogleAdsService.upload_material(existing, cfg=upload_cfg)
            except GoogleAdsUploadError as exc:
                return {
                    'api_status': 'error',
                    'material': None,
                    'conflict': None,
                    'google_ads': None,
                    'unity': None,
                    'error_message': str(exc),
                }
        elif channel == 'unity':
            try:
                unity = await UnityAdsService.upload_material(
                    existing, language=language, size=size, cfg=upload_cfg,
                )
            except UnityAdsUploadError as exc:
                return {
                    'api_status': 'error',
                    'material': None,
                    'conflict': None,
                    'google_ads': None,
                    'unity': None,
                    'error_message': str(exc),
                }
        elif channel not in CHANNELS:
            raise ParamsError

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

        external_id = ''
        if google_ads and google_ads.get('resource_name'):
            existing.google_ads_asset = google_ads['resource_name']
            external_id = google_ads['resource_name']
        if unity and unity.get('creative_id'):
            existing.unity_creative_id = unity['creative_id']
            external_id = unity['creative_id']

        if platform:
            token = await TokenConfig.find_one({'_id': ObjectId(platform.token_config_id)})
            publish_map = dict(existing.platform_publish or {})
            publish_map[channel] = {
                'platform_config_id': platform.id,
                'name': platform.name,
                'token_config_name': token.name if token else '',
                'external_id': external_id,
            }
            existing.platform_publish = publish_map

        existing.version = existing.version + 1
        existing.u_time = time10()
        await existing.save()
        if channel in _PUBLISH_CHANNELS:
            api_status = 'ok'
        else:
            api_status = 'stub'
        return {
            'api_status': api_status,
            'material': existing.info,
            'conflict': None,
            'google_ads': google_ads,
            'unity': unity,
        }

    @classmethod
    async def publish_stub(cls, material_id, version, channel, operator_id,
                           platform_config_id=None, language=None, size=None):
        return await cls.publish(
            material_id, version, channel, operator_id,
            platform_config_id=platform_config_id,
            language=language, size=size,
        )
