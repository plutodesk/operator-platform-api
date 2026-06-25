# -*- encoding: utf-8 -*-
#
# @Date: 2026

from seal.db.mongo import Mongo
from tornado.util import ObjectDict
from datetime import date, datetime
from bson.objectid import ObjectId


class BaseMongo(Mongo):
    structure = {}

    @property
    def id(self):
        return str(self._id)

    @property
    def info(self):
        ret = {'id': self.id}
        for key, value_type in self.structure.items():
            if key.startswith('_'):
                continue
            value = getattr(self, key, None)
            if value is not None:
                ret[key] = self.format_value(value)
            else:
                ret[key] = None
        return ObjectDict(ret)

    @staticmethod
    def format_value(obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, dict):
            return {key: BaseMongo.format_value(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [BaseMongo.format_value(item) for item in obj]
        else:
            return obj
