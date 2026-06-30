# -*- encoding: utf-8 -*-
"""Shared helpers for Google Ads asset upload test scripts."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import time
from pathlib import Path

import requests
import yaml

API_VERSION = 'v24'
DEFAULT_CUSTOMER_ID = '8969851272'
REPO_ROOT = Path(__file__).resolve().parents[2]
CONF_PATH = Path(__file__).resolve().parents[1] / 'conf.yaml'
CLIENT_SECRET_PATH = REPO_ROOT / 'client_secret_final.json'
POLL_INTERVAL_SEC = 10
POLL_TIMEOUT_SEC = 600


def load_config() -> dict:
    with CONF_PATH.open(encoding='utf-8') as fh:
        conf = yaml.safe_load(fh)
    with CLIENT_SECRET_PATH.open(encoding='utf-8') as fh:
        oauth = json.load(fh)['web']
    ads = conf.get('GOOGLE_ADS_CONFIG') or conf.get('GOOGLE_ADS_KEY') or {}
    developer_token = (
        (ads.get('DeveloperToken') or '').strip()
        or os.environ.get('GOOGLE_ADS_DEVELOPER_TOKEN', '').strip()
    )
    refresh_token = (ads.get('RefreshToken') or '').strip()
    customer_id = str(
        ads.get('CustomerId')
        or os.environ.get('GOOGLE_ADS_CUSTOMER_ID', DEFAULT_CUSTOMER_ID)
    ).replace('-', '').strip()
    if not refresh_token:
        raise SystemExit('Missing RefreshToken in conf.yaml GOOGLE_ADS_CONFIG')
    if not developer_token:
        raise SystemExit(
            'Missing DeveloperToken. Set GOOGLE_ADS_CONFIG.DeveloperToken in conf.yaml '
            'or export GOOGLE_ADS_DEVELOPER_TOKEN.'
        )
    return {
        'developer_token': developer_token,
        'refresh_token': refresh_token,
        'customer_id': customer_id,
        'client_id': oauth['client_id'],
        'client_secret': oauth['client_secret'],
        'login_customer_id': (
            (ads.get('LoginCustomerId') or os.environ.get('GOOGLE_ADS_LOGIN_CUSTOMER_ID', '')).replace('-', '').strip()
        ),
    }


def refresh_access_token(cfg: dict) -> str:
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
        raise SystemExit(f'Failed to refresh access token: {resp.status_code} {resp.text}')
    token = resp.json().get('access_token')
    if not token:
        raise SystemExit(f'No access_token in refresh response: {resp.text}')
    print('[ok] access token refreshed')
    return token


def ads_headers(cfg: dict, access_token: str, extra: dict | None = None) -> dict:
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


def file_fingerprint(path: Path) -> str:
    digest = hashlib.md5()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def text_fingerprint(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:12]


def mutate_assets(cfg: dict, access_token: str, operations: list) -> list:
    customer_id = cfg['customer_id']
    resp = requests.post(
        f'https://googleads.googleapis.com/{API_VERSION}/customers/{customer_id}/assets:mutate',
        headers=ads_headers(cfg, access_token),
        json={'operations': operations},
        timeout=60,
    )
    if resp.status_code != 200:
        raise SystemExit(f'assets:mutate failed: {resp.status_code}\n{resp.text}')
    results = resp.json().get('results') or []
    if not results:
        raise SystemExit(f'assets:mutate returned no results: {resp.text}')
    return results


def upload_text_asset(cfg: dict, access_token: str, text: str, name_prefix: str = 'text') -> dict:
    fp = text_fingerprint(text)
    asset_name = f'{name_prefix}_{fp}'
    results = mutate_assets(cfg, access_token, [{
        'create': {
            'name': asset_name,
            'type': 'TEXT',
            'textAsset': {'text': text},
        },
    }])
    resource_name = results[0].get('resourceName') or results[0].get('resource_name')
    print(f'[ok] TextAsset created: {resource_name}')
    return {
        'asset_name': asset_name,
        'resource_name': resource_name,
        'text': text,
    }


def _image_mime_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    mapping = {
        'image/jpeg': 'IMAGE_JPEG',
        'image/png': 'IMAGE_PNG',
        'image/gif': 'IMAGE_GIF',
    }
    if mime not in mapping:
        raise SystemExit(f'Unsupported image type: {path.suffix} ({mime})')
    return mapping[mime]


def upload_image_asset(cfg: dict, access_token: str, image_path: Path, name_prefix: str = 'image') -> dict:
    image_path = image_path.resolve()
    if not image_path.is_file():
        raise SystemExit(f'Image not found: {image_path}')
    fp = file_fingerprint(image_path)
    asset_name = f'{name_prefix}_{fp}'
    image_data = base64.b64encode(image_path.read_bytes()).decode('ascii')
    results = mutate_assets(cfg, access_token, [{
        'create': {
            'name': asset_name,
            'type': 'IMAGE',
            'imageAsset': {
                'data': image_data,
                'mimeType': _image_mime_type(image_path),
            },
        },
    }])
    resource_name = results[0].get('resourceName') or results[0].get('resource_name')
    print(f'[ok] ImageAsset created: {resource_name}')
    return {
        'asset_name': asset_name,
        'resource_name': resource_name,
        'image_path': str(image_path),
    }


def initiate_video_upload(
    cfg: dict,
    access_token: str,
    video_path: Path,
    title: str,
    description: str,
) -> tuple[str, int]:
    customer_id = cfg['customer_id']
    file_size = video_path.stat().st_size
    resp = requests.post(
        f'https://googleads.googleapis.com/resumable/upload/{API_VERSION}/customers/{customer_id}/youTubeVideoUploads:create',
        headers=ads_headers(cfg, access_token, {
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
        raise SystemExit(f'Failed to initiate video upload: {resp.status_code}\n{resp.text}')

    upload_url = resp.headers.get('x-goog-upload-url') or resp.headers.get('X-Goog-Upload-Url')
    if not upload_url:
        raise SystemExit(f'Missing x-goog-upload-url header. Response headers: {dict(resp.headers)}')

    chunk_size = int(
        resp.headers.get('x-goog-upload-chunk-granularity')
        or resp.headers.get('X-Goog-Upload-Chunk-Granularity')
        or file_size
    )
    print(f'[ok] video upload initiated, file_size={file_size}, chunk_size={chunk_size}')
    return upload_url, chunk_size


def upload_video_bytes(access_token: str, upload_url: str, video_path: Path, chunk_size: int) -> str:
    file_size = video_path.stat().st_size
    uploaded = 0
    resource_name = ''

    with video_path.open('rb') as fh:
        while uploaded < file_size:
            remaining = file_size - uploaded
            current_chunk = min(chunk_size, remaining)
            data = fh.read(current_chunk)
            is_last = uploaded + current_chunk >= file_size
            command = 'upload, finalize' if is_last else 'upload'
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-Goog-Upload-Offset': str(uploaded),
                'X-Goog-Upload-Command': command,
                'Content-Length': str(len(data)),
            }
            resp = requests.put(upload_url, headers=headers, data=data, timeout=300)
            if resp.status_code not in (200, 201):
                raise SystemExit(
                    f'Chunk upload failed at offset {uploaded}: {resp.status_code}\n{resp.text}'
                )
            uploaded += current_chunk
            pct = uploaded * 100 // file_size
            print(f'[upload] {uploaded}/{file_size} bytes ({pct}%)')
            if is_last and resp.text.strip():
                try:
                    body = resp.json()
                    resource_name = body.get('resourceName') or body.get('resource_name') or ''
                except json.JSONDecodeError:
                    pass

    if not resource_name:
        raise SystemExit('Upload finished but no resourceName returned in finalize response')
    print(f'[ok] video bytes uploaded: {resource_name}')
    return resource_name


def poll_video_state(cfg: dict, access_token: str, resource_name: str) -> dict:
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
            headers=ads_headers(cfg, access_token),
            json={'query': query},
            timeout=60,
        )
        if resp.status_code != 200:
            raise SystemExit(f'Failed to query upload state: {resp.status_code}\n{resp.text}')
        rows = resp.json().get('results') or []
        if rows:
            upload = rows[0].get('youTubeVideoUpload') or rows[0].get('you_tube_video_upload') or {}
            state = upload.get('state')
            video_id = upload.get('videoId') or upload.get('video_id')
            print(f'[poll] state={state}, video_id={video_id}')
            if state == 'PROCESSED' and video_id:
                return {'state': state, 'video_id': video_id, 'resource_name': resource_name}
            if state in ('FAILED', 'REJECTED', 'UNAVAILABLE'):
                raise SystemExit(f'Video upload ended with state={state}')
        time.sleep(POLL_INTERVAL_SEC)
    raise SystemExit(f'Timed out waiting for PROCESSED state after {POLL_TIMEOUT_SEC}s')


def upload_video_asset(cfg: dict, access_token: str, video_path: Path, name_prefix: str = 'video') -> dict:
    video_path = video_path.resolve()
    if not video_path.is_file():
        raise SystemExit(f'Video not found: {video_path}')
    fp = file_fingerprint(video_path)
    title = f'{name_prefix}_{fp}'
    description = f'Uploaded by operator-platform test script fingerprint={fp}'
    print(f'[info] customer_id={cfg["customer_id"]}, video={video_path}, title={title}')

    upload_url, chunk_size = initiate_video_upload(cfg, access_token, video_path, title, description)
    upload_resource = upload_video_bytes(access_token, upload_url, video_path, chunk_size)
    processed = poll_video_state(cfg, access_token, upload_resource)

    results = mutate_assets(cfg, access_token, [{
        'create': {
            'name': f'youtube_asset_{fp}',
            'type': 'YOUTUBE_VIDEO',
            'youtubeVideoAsset': {
                'youtubeVideoId': processed['video_id'],
            },
        },
    }])
    asset_resource = results[0].get('resourceName') or results[0].get('resource_name')
    print(f'[ok] YoutubeVideoAsset created: {asset_resource}')
    return {
        'upload_resource_name': upload_resource,
        'youtube_video_id': processed['video_id'],
        'asset_resource_name': asset_resource,
        'video_path': str(video_path),
    }
