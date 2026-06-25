# -*- encoding: utf-8 -*-
#
# @Date: 2026

from .base import BaseHandler
from operator_platform.db import Country

__all__ = [
    'CountryHandler',
]


class CountryHandler(BaseHandler):

    async def get(self):
        country_list = await Country.query({})
        result = [c.info for c in country_list]
        self.render({'countryList': result})
