# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'Country',
]


class Country(BaseMongo):
    structure = {
        'code': str,
        'en_name': str,
    }
