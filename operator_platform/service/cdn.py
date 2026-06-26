# -*- encoding: utf-8 -*-
#
# @Date: 2026

from seal.conf import options

__all__ = ['use_local_upload', 'effective_cdn_url']


def use_local_upload():
    local_upload = getattr(options, 'LOCAL_UPLOAD', None)
    if local_upload is not None:
        return bool(local_upload)
    return bool(options.LOCAL)


def effective_cdn_url():
    if use_local_upload() or options.DEBUG:
        return f'http://127.0.0.1:{options.PORT}/static/uploads/'
    cdn_url = (options.CDN_URL or '').strip()
    if not cdn_url:
        return ''
    return cdn_url if cdn_url.endswith('/') else f'{cdn_url}/'
