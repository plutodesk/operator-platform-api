# -*- encoding: utf-8 -*-
#
# @Date: 2026
"""One-shot import from conf.yaml GOOGLE_ADS_CONFIG / UNITY_CONFIG into MongoDB."""

from __future__ import annotations

import argparse
import asyncio

import operator_platform  # noqa: F401 — load conf.yaml
from seal.conf import options

from operator_platform.service.ad_platform_config import AdPlatformConfigService
from operator_platform.service.token_config import TokenConfigService


async def import_from_conf(force=False):
    google = getattr(options, 'GOOGLE_ADS_CONFIG', None) or {}
    unity = getattr(options, 'UNITY_CONFIG', None) or {}

    existing_tokens = await TokenConfigService.get_tokens()
    existing_configs = await AdPlatformConfigService.get_configs()
    if (existing_tokens or existing_configs) and not force:
        print('DB 已有配置，跳过。使用 --force 覆盖式追加。')
        return

    google_token = None
    if google.get('RefreshToken') and google.get('DeveloperToken'):
        google_token = await TokenConfigService.create_token(
            name='Google Ads 默认',
            channel='google',
            credentials={
                'refresh_token': google.get('RefreshToken') or '',
                'developer_token': google.get('DeveloperToken') or '',
            },
        )
        print('created google token:', google_token['id'])

    unity_token = None
    key_id = unity.get('key_id') or unity.get('KeyID') or ''
    secret_key = unity.get('secret_key') or unity.get('Secret key') or ''
    if key_id and secret_key:
        unity_token = await TokenConfigService.create_token(
            name='Unity 默认',
            channel='unity',
            credentials={
                'key_id': key_id,
                'secret_key': secret_key,
            },
        )
        print('created unity token:', unity_token['id'])

    if google_token and google.get('CustomerId'):
        cfg = await AdPlatformConfigService.create_config(
            name='Google Ads 默认',
            channel='google',
            product='',
            token_config_id=google_token['id'],
            settings={
                'customer_id': google.get('CustomerId') or '',
                'login_customer_id': google.get('LoginCustomerId') or '',
            },
        )
        print('created google platform config:', cfg['id'])

    org_id = unity.get('organization_id') or unity.get('OrganizationId') or ''
    app_id = unity.get('campaign_set_id') or unity.get('CampaignSetId') or ''
    if unity_token and org_id and app_id:
        cfg = await AdPlatformConfigService.create_config(
            name='Unity 默认',
            channel='unity',
            product='',
            token_config_id=unity_token['id'],
            settings={
                'organization_id': org_id,
                'campaign_set_id': app_id,
            },
        )
        print('created unity platform config:', cfg['id'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    asyncio.run(import_from_conf(force=args.force))


if __name__ == '__main__':
    main()
