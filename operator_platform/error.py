# -*- encoding: utf-8 -*-
#
# @Date: 2026

from seal.web.error import BaseWebError

__all__ = [
    'BaseError',
    'ParamsError',
    'AuthError',
]


class BaseError(BaseWebError):

    def __init__(self, message='Unknown Error', code=400):
        super().__init__(code, message)


class ParamsError(BaseError):

    def __init__(self):
        super(ParamsError, self).__init__('Params Error', 400)


class AuthError(BaseError):

    def __init__(self):
        super(AuthError, self).__init__('Not Login', 401)
