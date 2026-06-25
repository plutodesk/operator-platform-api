# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.error import ParamsError
from operator_platform.service.tag import TagService

__all__ = [
    'TagHandler',
]


class TagHandler(BaseHandler):

    async def get(self, discard=None):
        if discard:
            raise ParamsError
        result = await TagService.get_tags()
        self.render({'tagList': result})

    async def post(self, discard=None):
        if discard:
            raise ParamsError
        self.require_admin()
        self.add_json_argument('name', str, True)
        self.add_json_argument('color', str, False)
        self.add_json_argument('sort', int, False)
        result = await TagService.create_tag(
            name=self.json.name,
            color=getattr(self.json, 'color', '') or '',
            sort=getattr(self.json, 'sort', 0) or 0,
        )
        self.render(result)

    async def delete(self, tag_id=None):
        if not tag_id:
            raise ParamsError
        self.require_admin()
        await TagService.delete_tag(tag_id)
        self.render()
