# -*- encoding: utf-8 -*-
#
# @Date: 2026

from bson.objectid import ObjectId

from seal.conf import options

from operator_platform.db import AdPlatformConfig
from operator_platform.error import ParamsError
from operator_platform.service.ad_platform_config import AdPlatformConfigService
from operator_platform.service.token_config import TokenConfigService

__all__ = [
    'AdsConfigResolver',
]


class AdsConfigResolver(object):

    @classmethod
    def _oauth_client_secret(cls):
        secret = (getattr(options, 'OAUTH_CLIENT_SECRET', None) or '').strip()
        if secret:
            return secret
        legacy = getattr(options, 'GOOGLE_ADS_CONFIG', None) or {}
        return (legacy.get('ClientSecret') or '').strip()

    @classmethod
    def _build_google_cfg(cls, platform, credentials):
        settings = platform.settings or {}
        client_id = (options.OAUTH_CLIENT_ID or '').strip()
        client_secret = cls._oauth_client_secret()
        customer_id = str(settings.get('customer_id') or '').replace('-', '').strip()
        if not all([
            client_id,
            client_secret,
            credentials.get('refresh_token'),
            credentials.get('developer_token'),
            customer_id,
        ]):
            raise ParamsError
        return {
            'developer_token': credentials['developer_token'],
            'refresh_token': credentials['refresh_token'],
            'client_id': client_id,
            'client_secret': client_secret,
            'customer_id': customer_id,
            'login_customer_id': str(settings.get('login_customer_id') or '').replace('-', '').strip(),
        }

    @classmethod
    def _build_unity_cfg(cls, platform, credentials):
        settings = platform.settings or {}
        key_id = credentials.get('key_id') or ''
        secret_key = credentials.get('secret_key') or ''
        organization_id = str(settings.get('organization_id') or '').strip()
        campaign_set_id = str(settings.get('campaign_set_id') or '').strip()
        if not all([key_id, secret_key, organization_id, campaign_set_id]):
            raise ParamsError
        return {
            'key_id': key_id,
            'secret_key': secret_key,
            'organization_id': organization_id,
            'campaign_set_id': campaign_set_id,
        }

    @classmethod
    async def resolve_google(cls, product=None):
        platform = await AdPlatformConfigService.resolve_platform_config('google', product=product)
        credentials = await TokenConfigService.get_decrypted_credentials(platform.token_config_id)
        return cls._build_google_cfg(platform, credentials)

    @classmethod
    async def resolve_unity(cls, product=None):
        platform = await AdPlatformConfigService.resolve_platform_config('unity', product=product)
        credentials = await TokenConfigService.get_decrypted_credentials(platform.token_config_id)
        return cls._build_unity_cfg(platform, credentials)

    @classmethod
    async def resolve_by_config_id(cls, platform_config_id):
        try:
            config_oid = ObjectId(platform_config_id)
        except Exception as exc:
            raise ParamsError from exc
        platform = await AdPlatformConfig.find_one({'_id': config_oid})
        if not platform or not platform.enabled:
            raise ParamsError
        credentials = await TokenConfigService.get_decrypted_credentials(platform.token_config_id)
        if platform.channel == 'google':
            return platform, cls._build_google_cfg(platform, credentials)
        if platform.channel == 'unity':
            return platform, cls._build_unity_cfg(platform, credentials)
        raise ParamsError
