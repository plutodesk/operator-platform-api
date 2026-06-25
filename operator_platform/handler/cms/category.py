# -*- encoding: utf-8 -*-
#
# @Date: 2026


from .base import BaseHandler
from operator_platform.error import ParamsError
from operator_platform.service import CategoryService
from operator_platform.db import Country

__all__ = [
    'CategoryHandler',
    'CategorySortHandler',
    'CountryHandler',
]


class CountryHandler(BaseHandler):

    async def get(self):
        country_list = await Country.query({})
        result = [c.info for c in country_list]
        self.render({'countryList': result})


class CategoryHandler(BaseHandler):

    async def get(self, discard=None):
        if discard:
            raise ParamsError
        result = await CategoryService.get_categories()
        self.render({'categoryList': result})

    async def post(self, discard=None):
        if discard:
            raise ParamsError
        self.add_json_argument('key', str, True)
        self.add_json_argument('i18n_name', dict, True)
        self.add_json_argument('resource', str, True)
        self.add_json_argument('include_country', list, True)
        self.add_json_argument('exclude_country', list, True)
        result = await CategoryService.create_category(
            key=self.json.key,
            i18n_name=self.json.i18n_name,
            resource=self.json.resource,
            include_country=self.json.include_country,
            exclude_country=self.json.exclude_country,
        )
        self.render(result)

    async def put(self, category_id=None):
        if not category_id:
            raise ParamsError
        self.add_json_argument('i18n_name', dict, True)
        self.add_json_argument('resource', str, True)
        self.add_json_argument('active', bool, True)
        self.add_json_argument('include_country', list, True)
        self.add_json_argument('exclude_country', list, True)
        result = await CategoryService.update_category(
            category_id,
            i18n_name=self.json.i18n_name,
            resource=self.json.resource,
            include_country=self.json.include_country,
            exclude_country=self.json.exclude_country,
            active=self.json.active,
        )
        self.render(result)

    async def delete(self, category_id=None):
        if not category_id:
            raise ParamsError
        await CategoryService.delete_category(category_id)
        self.render()


class CategorySortHandler(BaseHandler):

    async def post(self):
        self.add_json_argument('sort', list, True)
        await CategoryService.sort_category(self.json.sort)
        self.render()
