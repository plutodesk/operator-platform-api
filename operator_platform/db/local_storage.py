# -*- encoding: utf-8 -*-
#
# @Date: 2026

import os

__all__ = ['UPLOAD_ROOT', 'put_blob_local']

UPLOAD_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '..',
    'static',
    'uploads',
))


def put_blob_local(relative_name, data):
    path = os.path.join(UPLOAD_ROOT, relative_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
