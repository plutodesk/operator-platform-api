# -*- encoding: utf-8 -*-
"""Shared helpers for Unity Acquire API test scripts."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import requests
import yaml

BASE_URL = 'https://services.api.unity.com/advertise/v1'
CONF_PATH = Path(__file__).resolve().parents[1] / 'conf.yaml'
DEFAULT_ORG_ID = '1375631575107'
DEFAULT_CAMPAIGN_SET_ID = '68f60802872bd4a7a9d50071'


def load_config() -> dict:
    key_id = os.environ.get('UNITY_KEY_ID', '').strip()
    secret_key = os.environ.get('UNITY_SECRET_KEY', '').strip()
    org_id = os.environ.get('UNITY_ORG_ID', DEFAULT_ORG_ID).strip()
    campaign_set_id = os.environ.get('UNITY_CAMPAIGN_SET_ID', DEFAULT_CAMPAIGN_SET_ID).strip()

    if CONF_PATH.exists() and (not key_id or not secret_key):
        conf = yaml.safe_load(CONF_PATH.read_text(encoding='utf-8')) or {}
        unity = conf.get('UNITY_CONFIG') or {}
        if isinstance(unity, dict):
            key_id = key_id or str(unity.get('key_id') or unity.get('KeyID') or '').strip()
            secret_key = secret_key or str(
                unity.get('secret_key') or unity.get('Secret key') or ''
            ).strip()
            org_id = org_id or str(
                unity.get('organization_id') or unity.get('OrganizationId') or DEFAULT_ORG_ID
            ).strip()
            campaign_set_id = campaign_set_id or str(
                unity.get('campaign_set_id') or unity.get('CampaignSetId') or DEFAULT_CAMPAIGN_SET_ID
            ).strip()

    if not key_id or not secret_key:
        raise SystemExit(
            'Missing Unity credentials. Export UNITY_KEY_ID / UNITY_SECRET_KEY '
            'or fix UNITY_CONFIG in conf.yaml.'
        )
    return {
        'key_id': key_id,
        'secret_key': secret_key,
        'organization_id': org_id,
        'campaign_set_id': campaign_set_id,
    }


def auth_header(cfg: dict) -> dict:
    token = base64.b64encode(f"{cfg['key_id']}:{cfg['secret_key']}".encode()).decode()
    return {'Authorization': f'Basic {token}'}


def request_json(method: str, url: str, cfg: dict, **kwargs) -> tuple[int, dict | str]:
    headers = {**auth_header(cfg), **kwargs.pop('headers', {})}
    resp = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    try:
        body: dict | str = resp.json()
    except ValueError:
        body = resp.text or '(empty body)'
    return resp.status_code, body


def print_result(label: str, status: int, body: dict | str) -> None:
    print(f'\n========== {label} ==========')
    print(f'[HTTP {status}]')
    if isinstance(body, dict):
        print(json.dumps(body, indent=2, ensure_ascii=False))
    else:
        print(body)
