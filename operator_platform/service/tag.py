# -*- encoding: utf-8 -*-
#
# @Date: 2026

from operator_platform.db import Tag
from operator_platform.error import ParamsError
from seal.utils.tools import time10

__all__ = [
    'TagService',
]


class TagService(object):

    @classmethod
    async def get_tags(cls):
        tag_list = await Tag.query({}, sort=[('sort', 1), ('c_time', 1)])
        return [tag.info for tag in tag_list]

    @classmethod
    async def create_tag(cls, name, color='', sort=0):
        name = (name or '').strip()
        if not name:
            raise ParamsError
        if await Tag.find_one({'name': name}):
            raise ParamsError
        tag = Tag(name=name, color=color or '', sort=sort or 0, c_time=time10())
        await tag.save()
        return tag.info

    @classmethod
    async def delete_tag(cls, tag_id):
        from bson.objectid import ObjectId
        try:
            oid = ObjectId(tag_id)
        except Exception:
            raise ParamsError
        tag = await Tag.find_one_and_delete({'_id': oid})
        if not tag:
            raise ParamsError
        return tag.info
