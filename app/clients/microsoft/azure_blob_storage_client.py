import os
from typing import NamedTuple
import uuid
from azure.storage.blob import BlobServiceClient
from fastapi import File


CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
CONTAINER_NAME = os.getenv('AZURE_CONTAINER_NAME', '')


class UploadFileReturn(NamedTuple):
    url: str | None
    filename: str | None


class AzureBlobStorageClient:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)


    def upload_file(self, file: File, filename: str) -> UploadFileReturn:
        try:
            extension = filename.split('.')[-1]
            filename = f'{uuid.uuid4()}.{extension}'

            blob_client = self.blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            blob_client.upload_blob(file, overwrite=True)

            return f'https://{self.blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{filename}', filename
        except Exception as e:
            # TODO: throw exception
            print(f'Error while uploading file: {e}')
            return None, None


    def delete_file(self, filename: str) -> bool:
        try:
            blob_client = self.blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
            blob_client.delete_blob()
            return True
        except Exception as e:
            # TODO: throw exception
            print(f'Error while deleting file: {e}')
            return False
