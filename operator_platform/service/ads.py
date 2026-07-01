# -*- encoding: utf-8 -*-
#
# @Date: 2026

import asyncio

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
    def _all_upload_paths(cls, material):
        paths = material.upload_paths or []
        if paths:
            return [p for p in paths if p]
        if material.upload_path:
            return [material.upload_path]
        return []

    @classmethod
    def _published_paths(cls, material, channel):
        publish = material.platform_publish or {}
        entry = publish.get(channel) or {}
        assets = entry.get('assets') or []
        if assets:
            return [a.get('upload_path') for a in assets if a.get('upload_path')]
        if entry.get('external_id') or cls._channel_published(material, channel):
            all_paths = cls._all_upload_paths(material)
            return [all_paths[0]] if all_paths else []
        return []

    @classmethod
    def _resolve_targets(cls, material, channel, upload_paths):
        published = set(cls._published_paths(material, channel))
        pending = [p for p in cls._all_upload_paths(material) if p not in published]
        if upload_paths:
            allowed = set(cls._all_upload_paths(material))
            pending_set = set(pending)
            pending = [p for p in upload_paths if p in allowed and p in pending_set]
        if not pending:
            raise ParamsError
        return pending

    @classmethod
    def _append_platform_asset(cls, material, channel, platform, token,
                               upload_path, external_id, asset_type):
        publish_map = dict(material.platform_publish or {})
        entry = dict(publish_map.get(channel) or {})
        assets = list(entry.get('assets') or [])
        assets.append({
            'upload_path': upload_path,
            'external_id': external_id,
            'asset_type': asset_type,
        })
        entry['assets'] = assets
        entry['external_id'] = external_id
        if platform:
            entry['platform_config_id'] = platform.id
            entry['name'] = platform.name
            entry['token_config_name'] = token.name if token else ''
        publish_map[channel] = entry
        material.platform_publish = publish_map
        if channel == 'google' and external_id:
            material.google_ads_asset = external_id
        elif channel == 'unity' and external_id:
            material.unity_creative_id = external_id

    @classmethod
    def _apply_publish_metadata(cls, material, channel, operator_id, language=None, size=None):
        usage = dict(material.channel_usage or {})
        usage[channel] = True
        material.channel_usage = usage
        operators = list(material.ads_operator_ids or [])
        if operator_id and operator_id not in operators:
            operators.append(operator_id)
        material.ads_operator_ids = operators
        if language:
            material.language = language
        if size:
            material.size = size

    @classmethod
    def _publish_response(cls, api_status, material=None, conflict=None,
                          google_ads=None, unity=None, succeeded=None, failed=None,
                          error_message=None):
        result = {
            'api_status': api_status,
            'material': material,
            'conflict': conflict,
            'google_ads': google_ads,
            'unity': unity,
            'succeeded': succeeded or [],
            'failed': failed or [],
        }
        if error_message is not None:
            result['error_message'] = error_message
        return result

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
                      platform_config_id=None, language=None, size=None, upload_paths=None):
        channel = (channel or '').strip().lower()
        if channel not in CHANNELS:
            raise ParamsError
        if channel in _PUBLISH_CHANNELS and not platform_config_id:
            raise ParamsError

        existing = await Material.find_one({'_id': MaterialService._object_id(material_id)})
        if not existing or existing.production_status != 'completed':
            raise ParamsError
        if existing.version != version:
            return cls._publish_response(
                'conflict',
                conflict={
                    'id': material_id,
                    'message': '数据已被他人更新，请刷新后再编辑',
                    'serverMaterial': existing.info,
                },
            )

        if channel not in _PUBLISH_CHANNELS:
            cls._apply_publish_metadata(existing, channel, operator_id, language, size)
            existing.version = existing.version + 1
            existing.u_time = time10()
            await existing.save()
            return cls._publish_response('stub', material=existing.info)

        targets = cls._resolve_targets(existing, channel, upload_paths)
        had_prior_publish = bool(cls._published_paths(existing, channel))

        platform, upload_cfg = await AdsConfigResolver.resolve_by_config_id(platform_config_id)
        cls._validate_platform_config(platform, channel, existing.product)
        token = await TokenConfig.find_one({'_id': ObjectId(platform.token_config_id)})

        succeeded = []
        failed = []
        last_google = None
        last_unity = None

        for upload_path in targets:
            try:
                if channel == 'google':
                    result = await asyncio.to_thread(
                        GoogleAdsService.upload_file, existing, upload_path, cfg=upload_cfg,
                    )
                    last_google = result
                    external_id = result.get('resource_name') or ''
                    asset_type = result.get('asset_type') or ''
                elif channel == 'unity':
                    result = await asyncio.to_thread(
                        UnityAdsService.upload_file, existing, upload_path,
                        language, size, upload_cfg,
                    )
                    last_unity = result
                    external_id = result.get('creative_id') or ''
                    asset_type = result.get('type') or ''
                else:
                    raise ParamsError

                cls._apply_publish_metadata(existing, channel, operator_id, language, size)
                cls._append_platform_asset(
                    existing, channel, platform, token,
                    upload_path, external_id, asset_type,
                )
                existing.version = existing.version + 1
                existing.u_time = time10()
                await existing.save()
                succeeded.append({
                    'upload_path': upload_path,
                    'external_id': external_id,
                    'asset_type': asset_type,
                })
            except (GoogleAdsUploadError, UnityAdsUploadError) as exc:
                failed.append({'upload_path': upload_path, 'error_message': str(exc)})

        if not succeeded and failed:
            error_message = failed[0]['error_message'] if len(failed) == 1 else None
            return cls._publish_response(
                'error',
                material=existing.info if had_prior_publish else None,
                google_ads=last_google,
                unity=last_unity,
                failed=failed,
                error_message=error_message,
            )

        if succeeded and failed:
            api_status = 'partial'
        else:
            api_status = 'ok'

        return cls._publish_response(
            api_status,
            material=existing.info,
            google_ads=last_google,
            unity=last_unity,
            succeeded=succeeded,
            failed=failed,
        )

    @classmethod
    async def publish_stub(cls, material_id, version, channel, operator_id,
                           platform_config_id=None, language=None, size=None,
                           upload_paths=None):
        return await cls.publish(
            material_id, version, channel, operator_id,
            platform_config_id=platform_config_id,
            language=language, size=size,
            upload_paths=upload_paths,
        )
