# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.error import ParamsError
from operator_platform.service.material import MaterialService
from operator_platform.service.resource import ResourceService

__all__ = [
    'MaterialHandler',
    'MaterialPublishHandler',
    'ResourceHandler',
]


def _split_ids(value):
    if not value:
        return []
    return [part for part in value.split(',') if part]


class MaterialHandler(BaseHandler):

    async def get(self):
        self.add_query_argument('page', int, False)
        self.add_query_argument('page_size', int, False)
        self.add_query_argument('keyword', str, False)
        self.add_query_argument('product', str, False)
        self.add_query_argument('tag_ids', str, False)
        self.add_query_argument('production_status', str, False)
        self.add_query_argument('producer_user_ids', str, False)
        self.add_query_argument('creative_user_ids', str, False)
        self.add_query_argument('material_type', str, False)
        self.add_query_argument('involvement', str, False)
        self.add_query_argument('language', str, False)
        self.add_query_argument('size', str, False)
        self.add_query_argument('completed_date_from', str, False)
        self.add_query_argument('completed_date_to', str, False)
        self.add_query_argument('channel', str, False)
        result = await MaterialService.list_materials(
            page=self.query.page or 1,
            page_size=self.query.page_size or 20,
            keyword=self.query.keyword,
            product=self.query.product,
            tag_ids=_split_ids(self.query.tag_ids),
            production_status=self.query.production_status,
            producer_user_ids=_split_ids(self.query.producer_user_ids),
            creative_user_ids=_split_ids(self.query.creative_user_ids),
            material_type=self.query.material_type,
            involvement=self.query.involvement,
            language=self.query.language,
            size=self.query.size,
            completed_date_from=self.query.completed_date_from,
            completed_date_to=self.query.completed_date_to,
            channels=_split_ids(self.query.channel),
            current_user_id=self.current_user['user_id'],
        )
        self.render({
            'materialList': result['items'],
            'total': result['total'],
            'page': result['page'],
            'pageSize': result['page_size'],
        })


class MaterialPublishHandler(BaseHandler):

    async def post(self):
        self.add_json_argument('creates', list, False)
        self.add_json_argument('updates', list, False)
        self.add_json_argument('deletes', list, False)
        result = await MaterialService.publish(
            creates=self.json.creates or [],
            updates=self.json.updates or [],
            deletes=self.json.deletes or [],
        )
        self.render(result)


class ResourceHandler(BaseHandler):

    async def post(self):
        if 'file' not in self.request.files:
            raise ParamsError
        prefix = self.get_argument('prefix', 'ads/material')
        result = await ResourceService.upload_resource(
            prefix=prefix,
            upload_file=self.request.files['file'][0],
        )
        self.render({'name': result})
