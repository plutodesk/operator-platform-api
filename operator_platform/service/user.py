# -*- encoding: utf-8 -*-
#
# @Date: 2026

from operator_platform.db import User
from seal.utils.tools import time10

__all__ = [
    'UserService',
]


class UserService(object):

    @classmethod
    async def get_users(cls):
        user_list = await User.query({})
        return [user.info for user in user_list]

    @classmethod
    async def login(cls, user):
        user = await User.find_one_and_update({
            'user_id': user['user_id']
        }, {
            '$set': user,
            '$setOnInsert': {
                'c_time': time10(),
            }
        }, upsert=True, return_document=True)
        return user.info

    @classmethod
    async def is_valid(cls, user):
        if not user:
            return False
        return bool(await User.find_one({'user_id': user['user_id']}))
