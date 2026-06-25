# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'Tag',
]


class Tag(BaseMongo):
    structure = {
        'name': str,
        'color': str,
        'sort': int,
        'c_time': int,
    }

    default = {
        'color': '',
        'sort': 0,
    }
