# operator_platform/service/resource.py
import hashlib
import os
from seal.conf import options
from operator_platform.db.gcs import GCSBucket

__all__ = ['ResourceService']

class ResourceService(object):
    @classmethod
    async def upload_resource(cls, prefix, upload_file):
        _, ext = os.path.splitext(upload_file['filename'])
        bucket = GCSBucket(options.BUCKET)
        name = f'{hashlib.md5(upload_file["body"]).hexdigest()}{ext}'
        if prefix:
            name = f'{prefix.strip("/")}/{name}'
        await bucket.put_blob_from_bytes(name, upload_file['body'], upload_file.get('content_type'))
        return name
