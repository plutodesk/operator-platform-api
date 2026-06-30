# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'AdPlatformConfig',
]

PLATFORM_CHANNELS = ['google', 'unity']


class AdPlatformConfig(BaseMongo):
    structure = {
        'name': str,
        'channel': str,
        'product': str,
        'token_config_id': str,
        'settings': dict,
        'enabled': bool,
        'c_time': int,
        'u_time': int,
    }

    default = {
        'product': '',
        'settings': {},
        'enabled': True,
    }
