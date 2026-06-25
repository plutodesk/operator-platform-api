# -*- encoding: utf-8 -*-
#
# @Date: 2026

from bson.objectid import ObjectId
from pymongo import UpdateOne
from seal.conf import options

from operator_platform.db import Category
from operator_platform.error import ParamsError
from .cache import cache_by_redis, remove_cache_by_redis

__all__ = [
    'CategoryService',
]


class CategoryService(object):

    @classmethod
    def _object_id(cls, category_id):
        try:
            return ObjectId(category_id)
        except Exception:
            raise ParamsError

    @classmethod
    @cache_by_redis(expire=3600)
    async def get_client_categories(cls, lang, country):
        spec = {
            'active': True,
            '$or': [
                {'include_country': {'$in': [country, None]}},
                {'include_country': {'$size': 0}},
            ],
            'exclude_country': {
                '$not': {
                    '$elemMatch': {'$eq': country},
                }
            },
        }
        category_list = await Category.query(spec, sort=[('sort', 1)])
        result = []
        for c in category_list:
            info = c.info
            i18n = info.pop('i18n_name', {}) or {}
            info['name'] = i18n.get(lang) or i18n.get('EN', '')
            if info.get('resource'):
                info['resource'] = options.CDN_URL + info['resource']
            for drop in ['include_country', 'exclude_country', 'active', 'sort']:
                info.pop(drop, None)
            result.append(info)
        return result

    @classmethod
    async def get_categories(cls):
        category_list = await Category.query({}, sort=[('sort', 1)])
        return [c.info for c in category_list]

    @classmethod
    async def create_category(cls, key, i18n_name, resource, include_country, exclude_country):
        if await Category.find_one({'key': key}):
            raise ParamsError
        category = Category(
            key=key,
            i18n_name=i18n_name,
            resource=resource,
            include_country=include_country,
            exclude_country=exclude_country,
            active=False,
            sort=0,
        )
        await category.save()
        remove_cache_by_redis(cls.get_client_categories)
        return category.info

    @classmethod
    async def update_category(cls, category_id, i18n_name, resource, include_country, exclude_country, active):
        category = await Category.find_one_and_update(
            {
                '_id': cls._object_id(category_id)
            }, {
                '$set': {
                    'i18n_name': i18n_name,
                    'resource': resource,
                    'include_country': include_country,
                    'exclude_country': exclude_country,
                    'active': active,
                }
            }, return_document=True
        )
        if not category:
            raise ParamsError
        remove_cache_by_redis(cls.get_client_categories)
        return category.info

    @classmethod
    async def delete_category(cls, category_id):
        category = await Category.find_one_and_delete({'_id': cls._object_id(category_id)})
        if not category:
            raise ParamsError
        remove_cache_by_redis(cls.get_client_categories)

    @classmethod
    async def sort_category(cls, sort):
        bulk = []
        for i, category_id in enumerate(sort):
            bulk.append(UpdateOne(
                {'_id': cls._object_id(category_id)},
                {'$set': {'sort': i}}
            ))
        if bulk:
            await Category.bulk_write(bulk)
            remove_cache_by_redis(cls.get_client_categories)
