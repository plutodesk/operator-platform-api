#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""Upload an IMAGE asset to Google Ads account 8969851272."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_ads_test_util import load_config, refresh_access_token, upload_image_asset

DEFAULT_IMAGE = Path(__file__).resolve().parents[1] / 'operator_platform/static/uploads/ads/material/2fa9ff1e1bd03a7075b3ad81c6918041.jpg'


def main() -> None:
    parser = argparse.ArgumentParser(description='Upload an image asset to Google Ads')
    parser.add_argument('--image', type=Path, default=DEFAULT_IMAGE, help='Path to jpg/png/gif')
    args = parser.parse_args()

    cfg = load_config()
    access_token = refresh_access_token(cfg)
    result = upload_image_asset(cfg, access_token, args.image)

    print('\n=== SUCCESS ===')
    print(json.dumps({
        'customer_id': cfg['customer_id'],
        **result,
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
