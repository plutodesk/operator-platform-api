# -*- encoding: utf-8 -*-
#
# @Date: 2026

import base64
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken
from seal.conf import options

__all__ = [
    'ConfigCryptoError',
    'encrypt_json',
    'decrypt_json',
    'mask_secret',
]


class ConfigCryptoError(Exception):
    pass


def _encryption_key_raw():
    key = (getattr(options, 'CONFIG_ENCRYPTION_KEY', None) or '').strip()
    if not key:
        key = (getattr(options, 'COFIG_SECRET', None) or '').strip()
    if not key:
        raise ConfigCryptoError('CONFIG_ENCRYPTION_KEY 未配置')
    return key


def _fernet():
    raw = _encryption_key_raw()
    try:
        return Fernet(raw.encode('utf-8'))
    except Exception:
        digest = hashlib.sha256(raw.encode('utf-8')).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_json(data):
    payload = json.dumps(data or {}, ensure_ascii=False, separators=(',', ':'))
    return _fernet().encrypt(payload.encode('utf-8')).decode('utf-8')


def decrypt_json(value):
    if not value:
        return {}
    try:
        payload = _fernet().decrypt(value.encode('utf-8'))
    except InvalidToken as exc:
        raise ConfigCryptoError('凭证解密失败，请检查 CONFIG_ENCRYPTION_KEY') from exc
    return json.loads(payload.decode('utf-8'))


def mask_secret(value, visible=4):
    text = str(value or '')
    if not text:
        return ''
    if len(text) <= visible * 2:
        return '*' * len(text)
    return f'{text[:visible]}…{text[-visible:]}'
