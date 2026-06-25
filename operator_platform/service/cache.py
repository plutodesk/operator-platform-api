# -*- encoding: utf-8 -*-
#
# @Date: 2026

import inspect
import msgpack
import logging
import redis
import copy
from seal.utils.tools import time10
from itertools import chain
from functools import wraps, partial
from typing import Callable, Any
from seal.conf import options
from seal.db.redis import redis_client as _redis_client

__all__ = [
    'cache_by_redis',
    'remove_cache_by_redis',
]


def _make_key(func: Callable, *args, **kwargs):
    """
    make cache key with func name & args & kwargs
    根据function & args & kwargs 生成缓存key

    :param func: function
    :param args: function`s args
    :param kwargs: function`s kwargs
    :return: key[str]
    """

    def parameter_check(x: Any):
        return (hasattr(x, '__str__')) and (isinstance(x, type) is False)

    cached_args = map(str, filter(parameter_check, args))
    cached_kwargs = [f'{k}={str(v)}' for k, v in filter(lambda pair: parameter_check(pair[1]), kwargs.items())]

    args_key = '_'.join(chain(cached_args, cached_kwargs))
    key = f'{func.__module__}.{func.__name__}.{args_key}'
    return key


def _cache(
        cache_writer: Callable[[str, object, int], None],
        cache_reader: Callable[[str], object],
        expire: int = 7200,
        key: str = None
) -> Callable:
    """
    general cache
    普通的缓存

    :param cache_writer: cache writer
    :param cache_reader: cache reader
    :param expire: cache expire
    :param key: cache key
    """

    def wrapper(func: Callable):
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def __inner_wrapper__(*args, **kwargs) -> object:
                cache_key = key or _make_key(func, *args, **kwargs)
                data = None
                if options.DEBUG:
                    data = await func(*args, **kwargs)
                else:
                    try:
                        data = cache_reader(cache_key)
                    except Exception as e:
                        logging.error(f'error when read cache {e} for {func.__module__}.{func.__name__}')
                    if data is None:
                        data = await func(*args, **kwargs)
                        try:
                            cache_writer(cache_key, data, expire)
                        except Exception as e:
                            logging.error(f'error when write cache {e} for {func.__module__}.{func.__name__}')
                return data
        else:
            @wraps(func)
            def __inner_wrapper__(*args, **kwargs) -> object:
                cache_key = key or _make_key(func, *args, **kwargs)
                data = None
                if options.DEBUG:
                    data = func(*args, **kwargs)
                else:
                    try:
                        data = cache_reader(cache_key)
                    except Exception as e:
                        logging.error(f'error when read cache {e} for {func.__module__}.{func.__name__}')
                    if data is None:
                        data = func(*args, **kwargs)
                        try:
                            cache_writer(cache_key, data, expire)
                        except Exception as e:
                            logging.error(f'error when write cache {e} for {func.__module__}.{func.__name__}')
                return data

        return __inner_wrapper__

    return wrapper


class MemoryCacher:
    """
    Memory Cache
    """
    __MEMORY_CACHE__ = dict()

    @classmethod
    def cache_writer(cls, key, data, expire):
        cls.__MEMORY_CACHE__[key] = {
            'data': data,
            'expire': expire + time10()
        }

    @classmethod
    def cache_reader(cls, key):
        if key not in cls.__MEMORY_CACHE__ or cls.__MEMORY_CACHE__[key]['expire'] < time10():
            return None
        return cls.__MEMORY_CACHE__[key]['data']

    @classmethod
    def remove_cache(cls, key):
        for sub_key in list(filter(lambda x: x.startswith(key), cls.__MEMORY_CACHE__)):
            cls.__MEMORY_CACHE__.pop(sub_key)


class RedisCacherMeta(type):
    _setter_client = None
    _getter_client = None
    _is_sentinel = None
    _sentinel_client = None

    @property
    def is_sentinel(cls):
        if cls._is_sentinel is None:
            try:
                from seal.db.redis import sentinel
                cls._is_sentinel = True
                cls._sentinel_client = sentinel
            except ImportError:
                cls._is_sentinel = False
                logging.error('sentinel not configured')
        return cls._is_sentinel

    @property
    def sentinel_client(cls):
        if not cls._sentinel_client:
            from seal.db.redis import sentinel
            cls._sentinel_client = sentinel
        return cls._sentinel_client

    @property
    def setter_client(cls):
        if not cls._setter_client:
            if cls.is_sentinel:
                redis_kwargs = copy.deepcopy(options.REDIS_SENTINEL.get('kwargs', {}))
                if redis_kwargs.get('decode_responses', False):
                    redis_kwargs['decode_responses'] = False
                cls._setter_client = cls.sentinel_client.master_for(options.REDIS_SENTINEL['clusterName'],
                                                                    **redis_kwargs)
            elif options.REDIS_KWARGS.get('decode_responses', False):
                redis_options = copy.deepcopy(options.REDIS_KWARGS)
                redis_options['decode_responses'] = False
                cls._setter_client = redis.from_url(options.REDIS_URL, **redis_options)
            else:
                cls._setter_client = _redis_client
        return cls._setter_client

    @property
    def getter_client(cls):
        if not cls._getter_client:
            if cls.is_sentinel:
                redis_kwargs = copy.deepcopy(options.REDIS_SENTINEL.get('kwargs', {}))
                if redis_kwargs.get('decode_responses', False):
                    redis_kwargs['decode_responses'] = False
                cls._getter_client = cls.sentinel_client.slave_for(options.REDIS_SENTINEL['clusterName'],
                                                                   **redis_kwargs)
            elif options.REDIS_KWARGS.get('decode_responses', False):
                redis_options = copy.deepcopy(options.REDIS_KWARGS)
                redis_options['decode_responses'] = False
                cls._getter_client = redis.from_url(options.REDIS_URL, **redis_options)
            else:
                cls._getter_client = _redis_client
        return cls._getter_client


class RedisCacher(metaclass=RedisCacherMeta):
    """
    Redis Cache
    """

    @classmethod
    def cache_writer(cls, key, data, expire):
        cls.setter_client.setex(key, expire, msgpack.dumps(data))

    @classmethod
    def cache_reader(cls, key: str):
        cache_result = cls.getter_client.get(key)
        if cache_result is not None:
            return msgpack.loads(cache_result)
        return None

    @classmethod
    def remove_cache(cls, key):
        cls._remove_cache(key)

    @classmethod
    def _remove_cache(cls, key):
        keys = cls.getter_client.keys(key + '*')
        if keys:
            with cls.setter_client.pipeline() as pipe:
                for k in keys:
                    pipe.delete(k)
                pipe.execute()


def _cache_key(func: Callable = None, key: str = None) -> str:
    if key is None and func is None:
        raise KeyError
    return key or _make_key(func)


def remove_cache_by_redis(func: Callable = None, *args, **kwargs):
    """
    remove cache by redis
    """
    cache_key = _make_key(func, *args, **kwargs)
    RedisCacher.remove_cache(cache_key)


cache_by_redis = partial(
    _cache,
    cache_writer=RedisCacher.cache_writer,
    cache_reader=RedisCacher.cache_reader
)
