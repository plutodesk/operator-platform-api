# operator_platform/service/resource.py
import hashlib
import logging
import os

from google.api_core.exceptions import Forbidden
from seal.conf import options

from operator_platform.db.gcs import GCSBucket
from operator_platform.db.local_storage import put_blob_local
from operator_platform.error import ParamsError

__all__ = ['ResourceService']

logger = logging.getLogger(__name__)


def _use_local_upload():
    local_upload = getattr(options, 'LOCAL_UPLOAD', None)
    if local_upload is not None:
        return bool(local_upload)
    return bool(options.LOCAL)


class ResourceService(object):
    @classmethod
    def _build_name(cls, prefix, upload_file):
        _, ext = os.path.splitext(upload_file['filename'])
        name = f'{hashlib.md5(upload_file["body"]).hexdigest()}{ext}'
        if prefix:
            name = f'{prefix.strip("/")}/{name}'
        return name

    @classmethod
    async def _upload_local(cls, name, upload_file):
        put_blob_local(name, upload_file['body'])
        return name

    @classmethod
    async def upload_resource(cls, prefix, upload_file):
        name = cls._build_name(prefix, upload_file)
        if _use_local_upload():
            return await cls._upload_local(name, upload_file)

        bucket_name = (options.BUCKET or '').strip()
        if not bucket_name:
            raise ParamsError

        bucket = GCSBucket(bucket_name)
        try:
            await bucket.put_blob_from_bytes(
                name,
                upload_file['body'],
                upload_file.get('content_type'),
            )
        except Forbidden:
            if not options.DEBUG:
                raise
            logger.warning(
                'GCS upload forbidden for %s, falling back to local storage',
                name,
            )
            return await cls._upload_local(name, upload_file)
        return name
