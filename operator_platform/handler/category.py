# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.service import CategoryService

__all__ = [
    'CategoryHandler',
]


class CategoryHandler(BaseHandler):

    async def get(self):
        result = await CategoryService.get_client_categories(
            lang=self.language,
            country=self.country,
        )
        self.render({'categoryList': result})
