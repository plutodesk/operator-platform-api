# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'TokenConfig',
]

TOKEN_CHANNELS = ['google', 'unity']


class TokenConfig(BaseMongo):
    structure = {
        'name': str,
        'channel': str,
        '_credentials_enc': str,
        'enabled': bool,
        'c_time': int,
        'u_time': int,
    }

    default = {
        'enabled': True,
    }
