#! /usr/bin/env python
# -*- coding: utf-8 -*-


import os
import logging
import tornado.ioloop
from seal.conf import options
from tornado.web import Application
from tornado.httpserver import HTTPServer

from operator_platform.handler.cms import *
from operator_platform.handler.cms.base import MeHandler, LogoutHandler
from operator_platform.handler.cms.debug import DebugLoginHandler, DebugUsersHandler

logger = logging.getLogger('tornado.general')
STATICS = os.path.join(os.path.dirname(__file__), 'static')
HANDLERS = [
    (r'/cms/v1/oauth2/login', OAuth2LoginHandler),
    (r'/cms/v1/me', MeHandler),
    (r'/cms/v1/logout', LogoutHandler),

    (r'/cms/v1/country', CountryHandler),
    (r'/cms/v1/ads/publish-options', AdsPublishOptionsHandler),
    (r'/cms/v1/ads/publish', AdsPublishHandler),
    (r'/cms/v1/material/publish', MaterialPublishHandler),
    (r'/cms/v1/material', MaterialHandler),
    (r'/cms/v1/resource', ResourceHandler),
    (r'/cms/v1/tag/(\w+)', TagHandler),
    (r'/cms/v1/tag', TagHandler),
    (r'/cms/v1/user/options', UserOptionsHandler),
    (r'/cms/v1/user/(\w+)', AdminUserHandler),
    (r'/cms/v1/user', AdminUserHandler),
    (r'/cms/v1/token-config/options', TokenConfigOptionsHandler),
    (r'/cms/v1/token-config/channels', TokenConfigChannelsHandler),
    (r'/cms/v1/token-config/(\w+)/test', TokenConfigTestHandler),
    (r'/cms/v1/token-config/(\w+)', TokenConfigHandler),
    (r'/cms/v1/token-config', TokenConfigHandler),
    (r'/cms/v1/ad-platform-config/(\w+)', AdPlatformConfigHandler),
    (r'/cms/v1/ad-platform-config', AdPlatformConfigHandler),
]
if options.LOCAL:
    HANDLERS.extend([
        (r'/cms/v1/debug/login', DebugLoginHandler),
        (r'/cms/v1/debug/users', DebugUsersHandler),
    ])

SETTINGS = {
    'debug': options.DEBUG,
    'gzip': True,
    'cookie_secret': 'operator_platform_cms_secret',
}


def main():
    http_server = HTTPServer(
        Application(HANDLERS, **SETTINGS),
        no_keep_alive=True,
    )
    http_server.listen(options.PORT)
    logger.info('listening on %d' % options.PORT)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    logger.info('starting operator_platform cms')
    main()
