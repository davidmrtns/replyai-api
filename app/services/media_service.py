from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.clients.microsoft.azure_blob_storage_client import AzureBlobStorageClient
from app.db.models import Media
from app.schemas.media_schema import CreateMediaSchema, UpdateMediaSchema
from app.utils.model_utils import apply_model_update, get_resource_from_db


def create_media(
    media_file: UploadFile, request: CreateMediaSchema, company_id: int, db: Session
):
    filename = f"{media_file.filename}"
    azure_blob_storage_client = AzureBlobStorageClient()

    file_url, upload_filename = azure_blob_storage_client.upload_file(
        media_file.file, filename
    )
    if file_url:
        mimetype = media_file.content_type
        media = Media(
            url=file_url,
            mediatype=mimetype,
            media_name=upload_filename,
            shortcut=request.shortcut,
            order=request.order,
            company_id=company_id,
        )

        db.add(media)
        db.commit()
        db.refresh(media)
        return media
    return None


def update_media(
    media_id: int, payload: UpdateMediaSchema, company_id: int | None, db: Session
):
    media = get_resource_from_db(Media, media_id, db, company_id)

    apply_model_update(media, payload)
    db.commit()
    db.refresh(media)
    return media


def delete_media(media_id: int, company_id: int | None, db: Session):
    azure_blob_storage_client = AzureBlobStorageClient()
    media = get_resource_from_db(Media, media_id, db, company_id)

    if azure_blob_storage_client.delete_file(media.media_name):
        db.delete(media)
        db.commit()
        return True
    return False
