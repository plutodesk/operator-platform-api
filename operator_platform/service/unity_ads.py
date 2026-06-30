# -*- encoding: utf-8 -*-
#
# @Date: 2026

import asyncio
import base64
import json
import logging
import mimetypes
import os

import requests
from seal.conf import options

from operator_platform.error import ParamsError
from operator_platform.service.ads_config import AdsConfigResolver
from operator_platform.service.cdn import effective_cdn_url, use_local_upload
from operator_platform.db.local_storage import UPLOAD_ROOT

__all__ = ['UnityAdsService', 'UnityAdsUploadError']

logger = logging.getLogger(__name__)

BASE_URL = 'https://services.api.unity.com/advertise/v1'


class UnityAdsUploadError(Exception):

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail or message


class UnityAdsService(object):

    @classmethod
    def _load_cfg(cls, cfg=None):
        if cfg:
            return cfg
        unity = getattr(options, 'UNITY_CONFIG', None) or {}
        key_id = str(unity.get('key_id') or unity.get('KeyID') or '').strip()
        secret_key = str(unity.get('secret_key') or unity.get('Secret key') or '').strip()
        organization_id = str(
            unity.get('organization_id') or unity.get('OrganizationId') or ''
        ).strip()
        campaign_set_id = str(
            unity.get('campaign_set_id') or unity.get('CampaignSetId') or ''
        ).strip()
        if not all([key_id, secret_key, organization_id, campaign_set_id]):
            raise UnityAdsUploadError('Unity 配置不完整')
        return {
            'key_id': key_id,
            'secret_key': secret_key,
            'organization_id': organization_id,
            'campaign_set_id': campaign_set_id,
        }

    @classmethod
    def _auth_headers(cls, cfg):
        token = base64.b64encode(
            f"{cfg['key_id']}:{cfg['secret_key']}".encode()
        ).decode()
        return {'Authorization': f'Basic {token}'}

    @classmethod
    def _primary_upload_path(cls, material):
        paths = material.upload_paths or []
        if paths:
            return paths[0]
        return material.upload_path or ''

    @classmethod
    def _fetch_upload_bytes(cls, upload_path):
        local_path = os.path.join(UPLOAD_ROOT, upload_path)
        if use_local_upload() and os.path.isfile(local_path):
            with open(local_path, 'rb') as fh:
                return fh.read()

        base = effective_cdn_url()
        if not base:
            raise UnityAdsUploadError('CDN 地址未配置，无法拉取素材')
        url = f"{base.rstrip('/')}/{upload_path.lstrip('/')}"
        resp = requests.get(url, timeout=180)
        if resp.status_code != 200:
            raise UnityAdsUploadError(
                f'从 CDN 拉取素材失败: {upload_path}',
                detail=resp.text[:500],
            )
        return resp.content

    @classmethod
    def _resolve_creative_spec(cls, material, language=None, size=None):
        material_type = material.material_type or ''
        size = (size or material.size or '').strip().lower()
        lang = (language or material.language or 'en').strip() or 'en'
        name = (material.name or 'material').strip()
        upload_path = cls._primary_upload_path(material)
        if not upload_path:
            raise ParamsError
        basename = os.path.basename(upload_path) or name

        if material_type == 'video':
            if size == '16x9':
                return {
                    'creative_info': {
                        'name': name,
                        'language': lang,
                        'landscapeVideo': {'fileName': basename},
                    },
                    'file_field': 'landscapeVideoFile',
                    'upload_path': upload_path,
                }
            return {
                'creative_info': {
                    'name': name,
                    'language': lang,
                    'video': {'fileName': basename},
                },
                'file_field': 'videoFile',
                'upload_path': upload_path,
            }

        if material_type == 'image':
            return {
                'creative_info': {
                    'name': name,
                    'language': lang,
                    'squareEndCard': {'fileName': basename},
                },
                'file_field': 'squareEndCardFile',
                'upload_path': upload_path,
            }

        raise ParamsError

    @classmethod
    def _upload_creative_sync(cls, material, language=None, size=None, cfg=None):
        cfg = cls._load_cfg(cfg)
        spec = cls._resolve_creative_spec(material, language=language, size=size)
        data = cls._fetch_upload_bytes(spec['upload_path'])
        upload_path = spec['upload_path']
        basename = os.path.basename(upload_path)
        mime, _ = mimetypes.guess_type(upload_path)
        mime = mime or 'application/octet-stream'
        url = (
            f"{BASE_URL}/organizations/{cfg['organization_id']}"
            f"/apps/{cfg['campaign_set_id']}/creatives"
        )
        resp = requests.post(
            url,
            headers=cls._auth_headers(cfg),
            files={
                'creativeInfo': (
                    None,
                    json.dumps(spec['creative_info']),
                    'application/json',
                ),
                spec['file_field']: (basename, data, mime),
            },
            timeout=300,
        )
        if resp.status_code not in (200, 201):
            detail = resp.text[:1000]
            try:
                body = resp.json()
                detail = body.get('detail') or body.get('title') or detail
            except ValueError:
                pass
            raise UnityAdsUploadError(
                f'Unity Creative 上传失败 (HTTP {resp.status_code})',
                detail=detail,
            )
        body = resp.json()
        creative_id = body.get('id') or ''
        if not creative_id:
            raise UnityAdsUploadError('Unity Creative 上传无 creative id', detail=resp.text)
        return {
            'creative_id': creative_id,
            'name': body.get('name') or spec['creative_info']['name'],
            'language': body.get('language') or spec['creative_info']['language'],
            'type': body.get('type') or '',
            'status': body.get('status') or '',
            'upload_path': upload_path,
        }

    @classmethod
    async def upload_material(cls, material, language=None, size=None, cfg=None):
        try:
            if cfg is None:
                cfg = await AdsConfigResolver.resolve_unity(product=getattr(material, 'product', None))
            result = await asyncio.to_thread(
                cls._upload_creative_sync, material, language, size, cfg,
            )
            logger.info(
                'Unity creative upload ok material=%s creative_id=%s',
                material.id,
                result.get('creative_id'),
            )
            return result
        except ParamsError as exc:
            raise UnityAdsUploadError('Unity 配置不完整') from exc
        except UnityAdsUploadError:
            raise
        except Exception as exc:
            logger.exception('Unity creative upload failed material=%s', material.id)
            raise UnityAdsUploadError('Unity Creative 上传失败', detail=str(exc)) from exc
