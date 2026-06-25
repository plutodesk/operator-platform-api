# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'User',
]


class User(BaseMongo):
    structure = {
        'user_id': str,
        'name': str,
        'avatar': str,
        'email': str,
        'c_time': int,
    }
