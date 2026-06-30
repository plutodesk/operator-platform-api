#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""Upload a local video to Google Ads via YouTubeVideoUploadService."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_ads_test_util import load_config, refresh_access_token, upload_video_asset

DEFAULT_VIDEO = Path('/Users/neptune/workspace/auto_ads_/test.mp4')


def main() -> None:
    parser = argparse.ArgumentParser(description='Upload a local mp4 to Google Ads account 8969851272')
    parser.add_argument('--video', type=Path, default=DEFAULT_VIDEO, help='Path to mp4 file')
    args = parser.parse_args()

    cfg = load_config()
    access_token = refresh_access_token(cfg)
    result = upload_video_asset(cfg, access_token, args.video)

    print('\n=== SUCCESS ===')
    print(json.dumps({
        'customer_id': cfg['customer_id'],
        **result,
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
