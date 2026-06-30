# -*- encoding: utf-8 -*-
#
# @Date: 2026

import asyncio

import requests
from bson.objectid import ObjectId
from seal.conf import options
from seal.utils.tools import time10

from operator_platform.db import AdPlatformConfig, TokenConfig
from operator_platform.error import ParamsError
from operator_platform.misc.crypto import ConfigCryptoError, decrypt_json, encrypt_json, mask_secret

__all__ = [
    'TokenConfigService',
]

GOOGLE_CREDENTIAL_KEYS = ['refresh_token', 'developer_token']
UNITY_CREDENTIAL_KEYS = ['key_id', 'secret_key']


class TokenConfigService(object):

    @classmethod
    def _object_id(cls, value):
        try:
            return ObjectId(value)
        except Exception as exc:
            raise ParamsError from exc

    @classmethod
    def _validate_channel(cls, channel):
        channel = (channel or '').strip().lower()
        if not channel:
            raise ParamsError
        return channel

    @classmethod
    def _is_google(cls, channel):
        return channel == 'google'

    @classmethod
    def _is_unity(cls, channel):
        return channel == 'unity'

    @classmethod
    def _normalize_credentials(cls, channel, credentials):
        credentials = credentials or {}
        if cls._is_google(channel):
            return {
                'refresh_token': (credentials.get('refresh_token') or '').strip(),
                'developer_token': (credentials.get('developer_token') or '').strip(),
            }
        if cls._is_unity(channel):
            return {
                'key_id': (credentials.get('key_id') or '').strip(),
                'secret_key': (credentials.get('secret_key') or '').strip(),
            }
        return {
            str(key).strip(): str(value).strip()
            for key, value in credentials.items()
            if str(key).strip() and str(value).strip()
        }

    @classmethod
    def _required_credential_keys(cls, channel):
        if cls._is_google(channel):
            return GOOGLE_CREDENTIAL_KEYS
        if cls._is_unity(channel):
            return UNITY_CREDENTIAL_KEYS
        return []

    @classmethod
    def _credentials_complete(cls, channel, credentials):
        required = cls._required_credential_keys(channel)
        if required:
            return all(credentials.get(key) for key in required)
        return bool(credentials)

    @classmethod
    def _credential_summary(cls, channel, credentials):
        credentials = credentials or {}
        if cls._is_google(channel):
            return {
                'refresh_token': mask_secret(credentials.get('refresh_token')),
                'developer_token': mask_secret(credentials.get('developer_token')),
            }
        if cls._is_unity(channel):
            return {
                'key_id': mask_secret(credentials.get('key_id'), visible=6),
                'secret_key': mask_secret(credentials.get('secret_key')),
            }
        return {
            str(key): mask_secret(value)
            for key, value in credentials.items()
        }

    @classmethod
    def _referencing_config_info(cls, config):
        return {
            'id': config.id,
            'name': config.name,
            'channel': config.channel,
            'product': config.product or '',
            'enabled': config.enabled,
        }

    @classmethod
    async def _referencing_config_map(cls, token_ids):
        token_ids = [str(token_id) for token_id in token_ids if token_id]
        if not token_ids:
            return {}
        configs = await AdPlatformConfig.query({'token_config_id': {'$in': token_ids}})
        result = {token_id: [] for token_id in token_ids}
        for config in configs:
            token_id = config.token_config_id
            if token_id in result:
                result[token_id].append(cls._referencing_config_info(config))
        for token_id in result:
            result[token_id].sort(key=lambda item: (item['channel'], item['product'], item['name']))
        return result

    @classmethod
    def _public_info(cls, token, referencing_configs=None):
        info = token.info
        try:
            credentials = decrypt_json(token._credentials_enc)
        except ConfigCryptoError:
            credentials = {}
        info['credentialSummary'] = cls._credential_summary(token.channel, credentials)
        info['referencingConfigList'] = referencing_configs if referencing_configs is not None else []
        return info

    @classmethod
    async def _public_info_async(cls, token):
        ref_map = await cls._referencing_config_map([token.id])
        return cls._public_info(token, ref_map.get(token.id, []))

    @classmethod
    async def get_tokens(cls):
        token_list = await TokenConfig.query({}, sort=[('channel', 1), ('c_time', 1)])
        if not token_list:
            return []
        ref_map = await cls._referencing_config_map([token.id for token in token_list])
        return [
            cls._public_info(token, ref_map.get(token.id, []))
            for token in token_list
        ]

    @classmethod
    async def get_options(cls):
        token_list = await TokenConfig.query({'enabled': True}, sort=[('channel', 1), ('name', 1)])
        return [
            {
                'id': token.id,
                'name': token.name,
                'channel': token.channel,
            }
            for token in token_list
        ]

    @classmethod
    async def get_token(cls, token_id):
        token = await TokenConfig.find_one({'_id': cls._object_id(token_id)})
        if not token:
            raise ParamsError
        return await cls._public_info_async(token)

    @classmethod
    async def get_channels(cls):
        token_list = await TokenConfig.query({}, sort=[('channel', 1), ('c_time', 1)])
        channels = []
        seen = set()
        for token in token_list:
            if token.channel and token.channel not in seen:
                seen.add(token.channel)
                channels.append(token.channel)
        return channels

    @classmethod
    async def get_decrypted_credentials(cls, token_id):
        token = await TokenConfig.find_one({'_id': cls._object_id(token_id)})
        if not token or not token.enabled:
            raise ParamsError
        raw = decrypt_json(token._credentials_enc)
        if cls._is_google(token.channel) or cls._is_unity(token.channel):
            return cls._normalize_credentials(token.channel, raw)
        return raw

    @classmethod
    async def create_token(cls, name, channel, credentials, enabled=True):
        name = (name or '').strip()
        channel = cls._validate_channel(channel)
        credentials = cls._normalize_credentials(channel, credentials)
        if not name or not cls._credentials_complete(channel, credentials):
            raise ParamsError
        now = time10()
        token = TokenConfig(
            name=name,
            channel=channel,
            _credentials_enc=encrypt_json(credentials),
            enabled=bool(enabled),
            c_time=now,
            u_time=now,
        )
        await token.save()
        return await cls._public_info_async(token)

    @classmethod
    async def _sync_referencing_configs_enabled(cls, token_id, enabled):
        now = time10()
        await AdPlatformConfig.update_many(
            {'token_config_id': str(token_id)},
            {'$set': {'enabled': bool(enabled), 'u_time': now}},
        )

    @classmethod
    async def update_token(cls, token_id, name=None, credentials=None, enabled=None):
        token = await TokenConfig.find_one({'_id': cls._object_id(token_id)})
        if not token:
            raise ParamsError
        if name is not None:
            name = (name or '').strip()
            if not name:
                raise ParamsError
            token.name = name
        if credentials is not None:
            merged = decrypt_json(token._credentials_enc)
            if cls._is_google(token.channel) or cls._is_unity(token.channel):
                incoming = cls._normalize_credentials(token.channel, credentials)
                for key in cls._required_credential_keys(token.channel):
                    if incoming.get(key):
                        merged[key] = incoming[key]
            else:
                incoming = cls._normalize_credentials(token.channel, credentials)
                merged.update(incoming)
            if not cls._credentials_complete(token.channel, merged):
                raise ParamsError
            token._credentials_enc = encrypt_json(merged)
        if enabled is not None:
            new_enabled = bool(enabled)
            if token.enabled != new_enabled:
                await cls._sync_referencing_configs_enabled(token.id, new_enabled)
            token.enabled = new_enabled
        token.u_time = time10()
        await token.save()
        return await cls._public_info_async(token)

    @classmethod
    async def delete_token(cls, token_id):
        oid = cls._object_id(token_id)
        in_use = await AdPlatformConfig.find_one({'token_config_id': str(oid)})
        if in_use:
            raise ParamsError
        token = await TokenConfig.find_one_and_delete({'_id': oid})
        if not token:
            raise ParamsError
        return await cls._public_info_async(token)

    @classmethod
    def _test_google_sync(cls, credentials):
        client_id = (options.OAUTH_CLIENT_ID or '').strip()
        client_secret = (getattr(options, 'OAUTH_CLIENT_SECRET', None) or '').strip()
        if not client_secret:
            legacy = getattr(options, 'GOOGLE_ADS_CONFIG', None) or {}
            client_secret = (legacy.get('ClientSecret') or '').strip()
        if not all([client_id, client_secret, credentials.get('refresh_token')]):
            return False, 'OAuth 或 Google Token 配置不完整'
        resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'grant_type': 'refresh_token',
                'client_id': client_id,
                'client_secret': client_secret,
                'refresh_token': credentials['refresh_token'],
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return False, resp.text[:300]
        if not resp.json().get('access_token'):
            return False, resp.text[:300]
        return True, 'Google Token 有效'

    @classmethod
    def _format_api_error(cls, resp):
        try:
            body = resp.json()
            detail = str(body.get('detail') or body.get('title') or resp.text)
            code = body.get('code')
            if resp.status_code in (401, 403) or 'not authorized' in detail.lower():
                return (
                    'Unity 鉴权失败（Not Authorized）：Key ID / Secret Key 无效、已过期，'
                    '或 Service Account 未授予 Advertise API Admin 权限。'
                    '请在 Unity Dashboard 核对后更新 Token 配置。'
                )
            if code:
                return f'{detail} (code={code})'
            return detail[:300]
        except Exception:
            return resp.text[:300]

    @classmethod
    def _test_unity_sync(cls, credentials, organization_id='', campaign_set_id=''):
        key_id = credentials.get('key_id') or ''
        secret_key = credentials.get('secret_key') or ''
        if not key_id or not secret_key:
            return False, 'Unity Token 配置不完整'
        organization_id = str(organization_id or '').strip()
        campaign_set_id = str(campaign_set_id or '').strip()
        if not organization_id or not campaign_set_id:
            return False, (
                '请先在「广告平台配置」中为该 Token 配置 '
                'organization_id 与 campaign_set_id'
            )
        import base64

        auth = base64.b64encode(f'{key_id}:{secret_key}'.encode()).decode()
        # 部分 Service Account 仅有 creatives 权限，list apps 会 403；与 test_unity_acquire.sh Step 2 一致
        url = (
            f'https://services.api.unity.com/advertise/v1'
            f'/organizations/{organization_id}/apps/{campaign_set_id}/creatives?limit=1'
        )
        resp = requests.get(
            url,
            headers={'Authorization': f'Basic {auth}'},
            timeout=30,
        )
        if resp.status_code != 200:
            return False, cls._format_api_error(resp)
        return True, 'Unity Token 有效（可访问 creatives）'

    @classmethod
    async def _unity_test_platform_settings(cls, token_id):
        config = await AdPlatformConfig.find_one({
            'token_config_id': token_id,
            'channel': 'unity',
            'enabled': True,
        })
        if not config:
            return '', ''
        settings = config.settings or {}
        org_id = str(settings.get('organization_id') or '').strip()
        app_id = str(settings.get('campaign_set_id') or '').strip()
        return org_id, app_id

    @classmethod
    async def test_token(cls, token_id):
        credentials = await cls.get_decrypted_credentials(token_id)
        token = await TokenConfig.find_one({'_id': cls._object_id(token_id)})
        if cls._is_google(token.channel):
            ok, message = await asyncio.to_thread(cls._test_google_sync, credentials)
        elif cls._is_unity(token.channel):
            org_id, app_id = await cls._unity_test_platform_settings(token.id)
            ok, message = await asyncio.to_thread(
                cls._test_unity_sync, credentials, org_id, app_id,
            )
        else:
            return {
                'ok': False,
                'message': f'平台「{token.channel}」暂不支持一键测试',
            }
        return {'ok': ok, 'message': message}
