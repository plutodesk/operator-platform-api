#! /usr/bin/env python
# -*- coding: utf-8 -*-


from tornado.web import RequestHandler
from .category import *


class PingHandler(RequestHandler):

    def get(self):
        self.write("pong")
