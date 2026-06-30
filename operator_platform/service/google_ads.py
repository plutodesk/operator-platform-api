# -*- encoding: utf-8 -*-
#
# @Date: 2026

import asyncio
import base64
import hashlib
import json
import logging
import mimetypes
import os
import re
import tempfile
import time
from pathlib import Path

import requests
from seal.conf import options

from operator_platform.db.local_storage import UPLOAD_ROOT
from operator_platform.error import ParamsError
from operator_platform.service.cdn import effective_cdn_url, use_local_upload

__all__ = ['GoogleAdsService', 'GoogleAdsUploadError']

logger = logging.getLogger(__name__)

API_VERSION = 'v24'
POLL_INTERVAL_SEC = 10
POLL_TIMEOUT_SEC = 600


class GoogleAdsUploadError(Exception):

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.detail = detail or message


class GoogleAdsService(object):

    @classmethod
    def _ads_config(cls):
        return getattr(options, 'GOOGLE_ADS_CONFIG', None) or {}

    @classmethod
    def _load_cfg(cls):
        ads = cls._ads_config()
        developer_token = (ads.get('DeveloperToken') or '').strip()
        refresh_token = (ads.get('RefreshToken') or '').strip()
        client_secret = (ads.get('ClientSecret') or '').strip()
        customer_id = str(ads.get('CustomerId') or '').replace('-', '').strip()
        client_id = (options.OAUTH_CLIENT_ID or '').strip()
        if not all([developer_token, refresh_token, client_secret, customer_id, client_id]):
            raise GoogleAdsUploadError('Google Ads 配置不完整')
        return {
            'developer_token': developer_token,
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'customer_id': customer_id,
            'login_customer_id': str(ads.get('LoginCustomerId') or '').replace('-', '').strip(),
        }

    @classmethod
    def _refresh_access_token(cls, cfg):
        resp = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'grant_type': 'refresh_token',
                'client_id': cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'refresh_token': cfg['refresh_token'],
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise GoogleAdsUploadError(
                '刷新 Google Ads AccessToken 失败',
                detail=resp.text,
            )
        token = resp.json().get('access_token')
        if not token:
            raise GoogleAdsUploadError('刷新 Google Ads AccessToken 失败', detail=resp.text)
        return token

    @classmethod
    def _ads_headers(cls, cfg, access_token, extra=None):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'developer-token': cfg['developer_token'],
            'Content-Type': 'application/json; charset=utf-8',
        }
        if cfg['login_customer_id']:
            headers['login-customer-id'] = cfg['login_customer_id']
        if extra:
            headers.update(extra)
        return headers

    @classmethod
    def _primary_upload_path(cls, material):
        paths = material.upload_paths or []
        if paths:
            return paths[0]
        return material.upload_path or ''

    @classmethod
    def _fingerprint_bytes(cls, data):
        return hashlib.md5(data).hexdigest()[:12]

    @classmethod
    def _fingerprint_text(cls, text):
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]

    @classmethod
    def _asset_name_prefix(cls, material, fingerprint):
        base = re.sub(r'[^\w\-]+', '_', (material.name or 'material').strip())[:40]
        return f'{base}_{fingerprint}'

    @classmethod
    def _fetch_upload_bytes(cls, upload_path):
        local_path = os.path.join(UPLOAD_ROOT, upload_path)
        if use_local_upload() and os.path.isfile(local_path):
            return Path(local_path).read_bytes()

        base = effective_cdn_url()
        if not base:
            raise GoogleAdsUploadError('CDN 地址未配置，无法拉取素材')
        url = f"{base.rstrip('/')}/{upload_path.lstrip('/')}"
        resp = requests.get(url, timeout=180)
        if resp.status_code != 200:
            raise GoogleAdsUploadError(
                f'从 CDN 拉取素材失败: {upload_path}',
                detail=resp.text[:500],
            )
        return resp.content

    @classmethod
    def _mutate_assets(cls, cfg, access_token, operations):
        customer_id = cfg['customer_id']
        resp = requests.post(
            f'https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/assets:mutate',
            headers=cls._ads_headers(cfg, access_token),
            json={'operations': operations},
            timeout=60,
        )
        if resp.status_code != 200:
            raise GoogleAdsUploadError('Google Ads assets:mutate 失败', detail=resp.text)
        results = resp.json().get('results') or []
        if not results:
            raise GoogleAdsUploadError('Google Ads assets:mutate 无结果', detail=resp.text)
        return results

    @classmethod
    def _image_mime_type(cls, upload_path):
        mime, _ = mimetypes.guess_type(upload_path)
        mapping = {
            'image/jpeg': 'IMAGE_JPEG',
            'image/png': 'IMAGE_PNG',
            'image/gif': 'IMAGE_GIF',
        }
        if mime not in mapping:
            raise GoogleAdsUploadError(f'不支持的图片格式: {upload_path}')
        return mapping[mime]

    @classmethod
    def _upload_text(cls, cfg, access_token, material, text):
        fp = cls._fingerprint_text(text)
        asset_name = cls._asset_name_prefix(material, fp)
        results = cls._mutate_assets(cfg, access_token, [{
            'create': {
                'name': asset_name,
                'type': 'TEXT',
                'textAsset': {'text': text},
            },
        }])
        resource_name = results[0].get('resourceName') or results[0].get('resource_name')
        return {
            'asset_type': 'TEXT',
            'asset_name': asset_name,
            'resource_name': resource_name,
        }

    @classmethod
    def _upload_image(cls, cfg, access_token, material, upload_path, data):
        fp = cls._fingerprint_bytes(data)
        asset_name = cls._asset_name_prefix(material, fp)
        image_data = base64.b64encode(data).decode('ascii')
        results = cls._mutate_assets(cfg, access_token, [{
            'create': {
                'name': asset_name,
                'type': 'IMAGE',
                'imageAsset': {
                    'data': image_data,
                    'mimeType': cls._image_mime_type(upload_path),
                },
            },
        }])
        resource_name = results[0].get('resourceName') or results[0].get('resource_name')
        return {
            'asset_type': 'IMAGE',
            'asset_name': asset_name,
            'resource_name': resource_name,
            'upload_path': upload_path,
        }

    @classmethod
    def _initiate_video_upload(cls, cfg, access_token, video_path, title, description):
        customer_id = cfg['customer_id']
        file_size = video_path.stat().st_size
        resp = requests.post(
            f'https://googleads.googleapis.com/resumable/upload/{API_VERSION}/customers/{customer_id}/youTubeVideoUploads:create',
            headers=cls._ads_headers(cfg, access_token, {
                'X-Goog-Upload-Protocol': 'resumable',
                'X-Goog-Upload-Command': 'start',
                'X-Goog-Upload-Header-Content-Length': str(file_size),
            }),
            json={
                'customer_id': customer_id,
                'you_tube_video_upload': {
                    'video_title': title,
                    'video_description': description,
                    'video_privacy': 'UNLISTED',
                },
            },
            timeout=60,
        )
        if resp.status_code not in (200, 201):
            raise GoogleAdsUploadError('发起 YouTube 视频上传失败', detail=resp.text)
        upload_url = resp.headers.get('x-goog-upload-url') or resp.headers.get('X-Goog-Upload-Url')
        if not upload_url:
            raise GoogleAdsUploadError('YouTube 上传缺少 x-goog-upload-url')
        chunk_size = int(
            resp.headers.get('x-goog-upload-chunk-granularity')
            or resp.headers.get('X-Goog-Upload-Chunk-Granularity')
            or file_size
        )
        return upload_url, chunk_size

    @classmethod
    def _upload_video_bytes(cls, access_token, upload_url, video_path, chunk_size):
        file_size = video_path.stat().st_size
        uploaded = 0
        resource_name = ''
        with video_path.open('rb') as fh:
            while uploaded < file_size:
                current_chunk = min(chunk_size, file_size - uploaded)
                data = fh.read(current_chunk)
                is_last = uploaded + current_chunk >= file_size
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'X-Goog-Upload-Offset': str(uploaded),
                    'X-Goog-Upload-Command': 'upload, finalize' if is_last else 'upload',
                    'Content-Length': str(len(data)),
                }
                resp = requests.put(upload_url, headers=headers, data=data, timeout=300)
                if resp.status_code not in (200, 201):
                    raise GoogleAdsUploadError(
                        f'YouTube 视频分块上传失败 offset={uploaded}',
                        detail=resp.text,
                    )
                uploaded += current_chunk
                if is_last and resp.text.strip():
                    try:
                        body = resp.json()
                        resource_name = body.get('resourceName') or body.get('resource_name') or ''
                    except json.JSONDecodeError:
                        pass
        if not resource_name:
            raise GoogleAdsUploadError('YouTube 视频上传完成但未返回 resourceName')
        return resource_name

    @classmethod
    def _poll_video_state(cls, cfg, access_token, resource_name):
        customer_id = cfg['customer_id']
        query = (
            'SELECT you_tube_video_upload.resource_name, '
            'you_tube_video_upload.video_id, '
            'you_tube_video_upload.state '
            f"FROM you_tube_video_upload WHERE you_tube_video_upload.resource_name = '{resource_name}'"
        )
        deadline = time.time() + POLL_TIMEOUT_SEC
        while time.time() < deadline:
            resp = requests.post(
                f'https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/googleAds:search',
                headers=cls._ads_headers(cfg, access_token),
                json={'query': query},
                timeout=60,
            )
            if resp.status_code != 200:
                raise GoogleAdsUploadError('查询 YouTube 视频状态失败', detail=resp.text)
            rows = resp.json().get('results') or []
            if rows:
                upload = rows[0].get('youTubeVideoUpload') or rows[0].get('you_tube_video_upload') or {}
                state = upload.get('state')
                video_id = upload.get('videoId') or upload.get('video_id')
                if state == 'PROCESSED' and video_id:
                    return video_id
                if state in ('FAILED', 'REJECTED', 'UNAVAILABLE'):
                    raise GoogleAdsUploadError(f'YouTube 视频处理失败: {state}')
            time.sleep(POLL_INTERVAL_SEC)
        raise GoogleAdsUploadError('YouTube 视频处理超时')

    @classmethod
    def _upload_video(cls, cfg, access_token, material, upload_path, data):
        fp = cls._fingerprint_bytes(data)
        asset_name = cls._asset_name_prefix(material, fp)
        suffix = os.path.splitext(upload_path)[1] or '.mp4'
        tmp_path = ''
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            video_path = Path(tmp_path)
            title = asset_name
            description = f'operator-platform material={material.id} fingerprint={fp}'
            upload_url, chunk_size = cls._initiate_video_upload(
                cfg, access_token, video_path, title, description,
            )
            upload_resource = cls._upload_video_bytes(access_token, upload_url, video_path, chunk_size)
            video_id = cls._poll_video_state(cfg, access_token, upload_resource)
            results = cls._mutate_assets(cfg, access_token, [{
                'create': {
                    'name': f'youtube_asset_{fp}',
                    'type': 'YOUTUBE_VIDEO',
                    'youtubeVideoAsset': {'youtubeVideoId': video_id},
                },
            }])
            resource_name = results[0].get('resourceName') or results[0].get('resource_name')
            return {
                'asset_type': 'YOUTUBE_VIDEO',
                'asset_name': asset_name,
                'resource_name': resource_name,
                'youtube_video_id': video_id,
                'upload_resource_name': upload_resource,
                'upload_path': upload_path,
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @classmethod
    def _upload_material_sync(cls, material):
        cfg = cls._load_cfg()
        access_token = cls._refresh_access_token(cfg)
        material_type = material.material_type or ''
        upload_path = cls._primary_upload_path(material)

        if material_type == 'video':
            if not upload_path:
                raise ParamsError
            data = cls._fetch_upload_bytes(upload_path)
            return cls._upload_video(cfg, access_token, material, upload_path, data)

        if material_type == 'image':
            if not upload_path:
                raise ParamsError
            data = cls._fetch_upload_bytes(upload_path)
            return cls._upload_image(cfg, access_token, material, upload_path, data)

        task_text = ''
        if isinstance(material.task_description, dict):
            task_text = (material.task_description.get('text') or '').strip()
        text = task_text or (material.name or '').strip()
        if text:
            return cls._upload_text(cfg, access_token, material, text)

        raise ParamsError

    @classmethod
    async def upload_material(cls, material):
        try:
            result = await asyncio.to_thread(cls._upload_material_sync, material)
            logger.info('Google Ads upload ok material=%s result=%s', material.id, result.get('resource_name'))
            return result
        except ParamsError:
            raise
        except GoogleAdsUploadError:
            raise
        except Exception as exc:
            logger.exception('Google Ads upload failed material=%s', material.id)
            raise GoogleAdsUploadError('Google Ads 上传失败', detail=str(exc)) from exc
