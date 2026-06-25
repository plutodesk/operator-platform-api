# operator_platform/db/gcs.py
from google.oauth2.service_account import Credentials
from google.cloud.storage.client import Client
from google.cloud.storage.bucket import Bucket
from google.cloud.storage.blob import Blob
from seal.conf import options
from seal.executor import RunExecutor
from tornado.concurrent import run_on_executor
import io

__all__ = ['GCSBucket']

class GCSBucket(Bucket, RunExecutor):
    def __init__(self, bucket_name):
        super().__init__(
            Client(credentials=Credentials.from_service_account_info(
                options.GC_KEY,
                scopes=['https://www.googleapis.com/auth/devstorage.read_write'],
            )),
            bucket_name,
        )

    @run_on_executor
    def put_blob_from_bytes(self, blob_name, data, content_type=None):
        blob = Blob(blob_name, self)
        file_obj = io.BytesIO(data)
        return blob.upload_from_file(file_obj, content_type=content_type)
