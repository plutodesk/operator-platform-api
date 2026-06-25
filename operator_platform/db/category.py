# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseMongo

__all__ = [
    'Category',
    'Country',
]


class Country(BaseMongo):
    structure = {
        'code': str,
        'en_name': str,
    }


class Category(BaseMongo):
    structure = {
        'key': str,
        'i18n_name': dict,
        'sort': int,
        'resource': str,
        'active': bool,
        'include_country': list,
        'exclude_country': list,
    }

    default = {
        'include_country': [],
        'exclude_country': [],
        'sort': 0,
        'active': False,
    }
