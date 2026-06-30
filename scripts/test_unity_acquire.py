#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""Unity Acquire API connectivity and creative upload test."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from unity_test_util import BASE_URL, load_config, print_result, request_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO = REPO_ROOT / 'test.mp4'


def main() -> None:
    parser = argparse.ArgumentParser(description='Test Unity Acquire API')
    parser.add_argument(
        '--upload',
        nargs='?',
        const=str(DEFAULT_VIDEO),
        help='Upload video file (default: repo test.mp4)',
    )
    parser.add_argument(
        '--orientation',
        choices=('portrait', 'landscape'),
        default='portrait',
        help='Video orientation for upload',
    )
    args = parser.parse_args()
    cfg = load_config()
    org_id = cfg['organization_id']
    app_id = cfg['campaign_set_id']

    status, body = request_json(
        'GET',
        f'{BASE_URL}/organizations/{org_id}/apps',
        cfg,
        params={'limit': 10},
    )
    print_result('Step 1: List Apps', status, body)

    status, body = request_json(
        'GET',
        f'{BASE_URL}/organizations/{org_id}/apps/{app_id}/creatives',
        cfg,
        params={'limit': 10},
    )
    print_result(f'Step 2: List Creatives (campaign set = {app_id})', status, body)

    if args.upload:
        video_path = Path(args.upload).resolve()
        if not video_path.is_file():
            raise SystemExit(f'Video not found: {video_path}')

        name = f'api-test-{datetime.now():%Y%m%d-%H%M%S}'
        basename = video_path.name
        if args.orientation == 'landscape':
            creative_info = {
                'name': name,
                'language': 'en',
                'landscapeVideo': {'fileName': basename},
            }
            file_field = 'landscapeVideoFile'
        else:
            creative_info = {
                'name': name,
                'language': 'en',
                'video': {'fileName': basename},
            }
            file_field = 'videoFile'

        with video_path.open('rb') as fh:
            status, body = request_json(
                'POST',
                f'{BASE_URL}/organizations/{org_id}/apps/{app_id}/creatives',
                cfg,
                files={
                    'creativeInfo': (None, json.dumps(creative_info), 'application/json'),
                    file_field: (basename, fh, 'application/octet-stream'),
                },
            )
        print_result(
            f'Step 3: Upload Creative ({args.orientation}: {video_path})',
            status,
            body,
        )

    print('\n完成。若 Step 1 返回 401/403，请检查 Service Account 是否启用了 Advertise API Admin 角色。')


if __name__ == '__main__':
    main()
