#! /usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import logging

from seal.conf import define, load_options


if sys.stdout.isatty():
    from tornado.log import enable_pretty_logging
    enable_pretty_logging()

define('LOCAL', default=False, help="LOCAL")
define('LOCAL_UPLOAD', default=None, help="Use local filesystem for uploads; defaults to LOCAL")
define('DEBUG', default=False, help="Debug")
define('PORT', default=20010, help="Port")
define('CDN_URL', default='', help='Asset CDN base url')
define('OAUTH_CLIENT_ID', default='', help='Google OAuth Client ID')
define('OAUTH_CLIENT_SECRET', default='', help='Google OAuth Client Secret')
define('OAUTH_EMAIL_DOMAIN', default='', help='Allowed login email domain, empty = allow all')
define('JWT_SECRET', default='change-me', help="JWT secret")
define('CONFIG_ENCRYPTION_KEY', default='', help='Fernet key for encrypting token credentials in DB')
define('COFIG_SECRET', default='', help='Deprecated alias for CONFIG_ENCRYPTION_KEY')
define('GC_KEY', default={}, help='Google cloud service account json')
define('BUCKET', default='', help='GCS bucket name')
define('GOOGLE_ADS_CONFIG', default={}, help='Deprecated Google Ads config fallback')
define('UNITY_CONFIG', default={}, help='Deprecated Unity config fallback')

config_path = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '../conf.yaml'
))
conf_str = os.getenv('APP_CONF', None)

if not conf_str:
    logging.info('environment "APP_CONF" not found')
    if os.path.exists(config_path):
        logging.info(f"found local config file at {config_path}")
        load_options(file_name=config_path)
    else:
        logging.warning(
            f'local config file {config_path} not found, '
            'run "python -m seal dump_conf operator_platform.index" '
            'to generate one or set APP_CONF'
        )
else:
    load_options(config_str=conf_str)
