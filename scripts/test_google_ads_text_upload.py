#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""Upload a TEXT asset to Google Ads account 8969851272."""

from __future__ import annotations

import argparse
import json

from google_ads_test_util import load_config, refresh_access_token, upload_text_asset


def main() -> None:
    parser = argparse.ArgumentParser(description='Upload a text asset to Google Ads')
    parser.add_argument(
        '--text',
        default='限时优惠，点击领取折扣',
        help='Text content for the asset',
    )
    args = parser.parse_args()

    cfg = load_config()
    access_token = refresh_access_token(cfg)
    result = upload_text_asset(cfg, access_token, args.text)

    print('\n=== SUCCESS ===')
    print(json.dumps({
        'customer_id': cfg['customer_id'],
        **result,
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
