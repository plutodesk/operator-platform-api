# -*- encoding: utf-8 -*-
#
# @Date: 2026

from bson.objectid import ObjectId
from seal.utils.tools import time10

from operator_platform.constants.products import PRODUCTS
from operator_platform.db import AdPlatformConfig, TokenConfig
from operator_platform.error import ParamsError

__all__ = [
    'AdPlatformConfigService',
]


class AdPlatformConfigService(object):

    @classmethod
    def _object_id(cls, value):
        try:
            return ObjectId(value)
        except Exception as exc:
            raise ParamsError from exc

    @classmethod
    def _is_google(cls, channel):
        return channel == 'google'

    @classmethod
    def _is_unity(cls, channel):
        return channel == 'unity'

    @classmethod
    async def _validate_channel(cls, channel):
        channel = (channel or '').strip().lower()
        if not channel:
            raise ParamsError
        exists = await TokenConfig.find_one({'channel': channel})
        if not exists:
            raise ParamsError
        return channel

    @classmethod
    def _normalize_settings(cls, channel, settings):
        settings = settings or {}
        if cls._is_google(channel):
            return {
                'customer_id': str(settings.get('customer_id') or '').replace('-', '').strip(),
                'login_customer_id': str(settings.get('login_customer_id') or '').replace('-', '').strip(),
            }
        if cls._is_unity(channel):
            return {
                'organization_id': str(settings.get('organization_id') or '').strip(),
                'campaign_set_id': str(settings.get('campaign_set_id') or '').strip(),
            }
        return {
            str(key).strip(): str(value).strip()
            for key, value in settings.items()
            if str(key).strip() and str(value).strip()
        }

    @classmethod
    def _validate_settings(cls, channel, settings):
        settings = cls._normalize_settings(channel, settings)
        if cls._is_google(channel):
            if not settings['customer_id']:
                raise ParamsError
        elif cls._is_unity(channel):
            if not settings['organization_id'] or not settings['campaign_set_id']:
                raise ParamsError
        elif not settings:
            raise ParamsError
        return settings

    @classmethod
    async def _validate_token_ref(cls, channel, token_config_id):
        token = await TokenConfig.find_one({'_id': cls._object_id(token_config_id)})
        if not token or not token.enabled or token.channel != channel:
            raise ParamsError
        return token.id

    @classmethod
    async def _ensure_name_unique(cls, name, exclude_id=None):
        existing = await AdPlatformConfig.find_one({'name': name})
        if existing and (exclude_id is None or existing.id != exclude_id):
            raise ParamsError

    @classmethod
    def _public_info(cls, config, token_name=''):
        info = config.info
        info['tokenConfigName'] = token_name
        return info

    @classmethod
    async def _token_name_map(cls, configs):
        token_ids = {cfg.token_config_id for cfg in configs if cfg.token_config_id}
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
    async def get_configs(cls):
        config_list = await AdPlatformConfig.query({}, sort=[('channel', 1), ('product', 1), ('c_time', 1)])
        token_names = await cls._token_name_map(config_list)
        return [
            cls._public_info(config, token_names.get(config.token_config_id, ''))
            for config in config_list
        ]

    @classmethod
    async def create_config(cls, name, channel, product, token_config_id, settings, enabled=True):
        name = (name or '').strip()
        channel = await cls._validate_channel(channel)
        product = (product or '').strip()
        if product and product not in PRODUCTS:
            raise ParamsError
        if not name:
            raise ParamsError
        await cls._ensure_name_unique(name)
        token_config_id = await cls._validate_token_ref(channel, token_config_id)
        settings = cls._validate_settings(channel, settings)
        now = time10()
        config = AdPlatformConfig(
            name=name,
            channel=channel,
            product=product,
            token_config_id=token_config_id,
            settings=settings,
            enabled=bool(enabled),
            c_time=now,
            u_time=now,
        )
        await config.save()
        token = await TokenConfig.find_one({'_id': ObjectId(token_config_id)})
        return cls._public_info(config, token.name if token else '')

    @classmethod
    async def update_config(cls, config_id, name=None, product=None, token_config_id=None, settings=None, enabled=None):
        config = await AdPlatformConfig.find_one({'_id': cls._object_id(config_id)})
        if not config:
            raise ParamsError
        if name is not None:
            name = (name or '').strip()
            if not name:
                raise ParamsError
            await cls._ensure_name_unique(name, exclude_id=config.id)
            config.name = name
        if product is not None:
            product = (product or '').strip()
            if product and product not in PRODUCTS:
                raise ParamsError
            config.product = product
        if token_config_id is not None:
            config.token_config_id = await cls._validate_token_ref(config.channel, token_config_id)
        if settings is not None:
            config.settings = cls._validate_settings(config.channel, settings)
        if enabled is not None:
            config.enabled = bool(enabled)
        config.u_time = time10()
        await config.save()
        token = await TokenConfig.find_one({'_id': ObjectId(config.token_config_id)})
        return cls._public_info(config, token.name if token else '')

    @classmethod
    async def delete_config(cls, config_id):
        config = await AdPlatformConfig.find_one_and_delete({'_id': cls._object_id(config_id)})
        if not config:
            raise ParamsError
        token = await TokenConfig.find_one({'_id': ObjectId(config.token_config_id)})
        return cls._public_info(config, token.name if token else '')

    @classmethod
    async def resolve_platform_config(cls, channel, product=None):
        channel = (channel or '').strip().lower()
        if not channel:
            raise ParamsError
        product = (product or '').strip()
        config = None
        if product:
            config = await AdPlatformConfig.find_one({
                'channel': channel,
                'product': product,
                'enabled': True,
            })
        if not config:
            config = await AdPlatformConfig.find_one({
                'channel': channel,
                'product': '',
                'enabled': True,
            })
        if not config:
            raise ParamsError
        return config
