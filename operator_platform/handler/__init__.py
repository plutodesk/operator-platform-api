#! /usr/bin/env python
# -*- coding: utf-8 -*-


from tornado.web import RequestHandler

__all__ = [
    'PingHandler',
]


class PingHandler(RequestHandler):

    def get(self):
        self.write("pong")
