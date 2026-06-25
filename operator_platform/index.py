#! /usr/bin/env python
# -*- coding: utf-8 -*-


import os
import logging
import tornado.ioloop
from tornado.web import Application, StaticFileHandler
from tornado.httpserver import HTTPServer

from seal.conf import options
from operator_platform.handler import *
from operator_platform.handler import PingHandler

logger = logging.getLogger('tornado.general')
STATICS = os.path.join(os.path.dirname(__file__), 'static')
HANDLERS = [
    (r'/_/ping', PingHandler),
    (r'/static/(.+)', StaticFileHandler, {'path': STATICS}),

    (r'/api/v1/category', CategoryHandler),
]

if options.DEBUG:
    logger.setLevel(logging.DEBUG)
    logging.getLogger('tornado.access').setLevel(logging.DEBUG)
    from operator_platform.handler.cms.index import HANDLERS as CMS_HANDLERS

    HANDLERS += CMS_HANDLERS

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
    logger.info('starting operator_platform')
    main()
