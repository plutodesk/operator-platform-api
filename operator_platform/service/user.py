# -*- encoding: utf-8 -*-
#
# @Date: 2026

from bson.objectid import ObjectId

from operator_platform.db import User
from operator_platform.error import ParamsError
from seal.utils.tools import time10

__all__ = [
    'UserService',
]


class UserService(object):

    @classmethod
    def _object_id(cls, user_id):
        try:
            return ObjectId(user_id)
        except Exception:
            raise ParamsError

    @classmethod
    async def get_users(cls):
        user_list = await User.query({}, sort=[('c_time', 1)])
        return [user.info for user in user_list]

    @classmethod
    async def get_user_options(cls):
        user_list = await User.query({'active': True}, sort=[('name', 1)])
        return [{'id': user.id, 'name': user.name, 'email': user.email} for user in user_list]

    @classmethod
    async def create_user(cls, email, name, role='user'):
        email = (email or '').strip().lower()
        name = (name or '').strip()
        if not email or not name:
            raise ParamsError
        if role not in ('user', 'admin'):
            raise ParamsError
        if await User.find_one({'email': email}):
            raise ParamsError
        user = User(
            user_id=f'manual:{email}',
            name=name,
            email=email,
            avatar='',
            role=role,
            active=True,
            c_time=time10(),
        )
        await user.save()
        return user.info

    @classmethod
    async def update_user(cls, user_id, role=None, active=None):
        oid = cls._object_id(user_id)
        update = {}
        if role is not None:
            if role not in ('user', 'admin'):
                raise ParamsError
            update['role'] = role
        if active is not None:
            update['active'] = active
        if not update:
            raise ParamsError
        user = await User.find_one_and_update(
            {'_id': oid},
            {'$set': update},
            return_document=True,
        )
        if not user:
            raise ParamsError
        return user.info

    @classmethod
    async def login(cls, user):
        existing = await User.find_one({'email': user['email']})
        if existing:
            user = await User.find_one_and_update(
                {'_id': existing._id},
                {
                    '$set': {
                        'user_id': user['user_id'],
                        'name': user['name'],
                        'email': user['email'],
                        'avatar': user.get('avatar', ''),
                    },
                    '$setOnInsert': {
                        'c_time': time10(),
                        'role': 'user',
                        'active': True,
                    },
                },
                upsert=True,
                return_document=True,
            )
            info = user.info
            if info.get('role') is None:
                info['role'] = 'user'
            if info.get('active') is None:
                info['active'] = True
            return info
        user = await User.find_one_and_update(
            {'user_id': user['user_id']},
            {
                '$set': user,
                '$setOnInsert': {
                    'c_time': time10(),
                    'role': 'user',
                    'active': True,
                },
            },
            upsert=True,
            return_document=True,
        )
        info = user.info
        if info.get('role') is None:
            info['role'] = 'user'
        if info.get('active') is None:
            info['active'] = True
        return info

    @classmethod
    async def is_valid(cls, user):
        if not user:
            return False
        doc = await User.find_one({'user_id': user['user_id']})
        if not doc:
            doc = await User.find_one({'email': user.get('email')})
        if not doc:
            return False
        if doc.active is False:
            return False
        return True

    @classmethod
    async def login_by_email(cls, email):
        user = await User.find_one({'email': email, 'active': True})
        if not user:
            raise ParamsError
        return user.info

    @classmethod
    async def list_active_users(cls):
        users = await User.query({'active': True}, sort=[('email', 1)])
        return [{'email': u.email, 'name': u.name, 'role': u.role} for u in users]
