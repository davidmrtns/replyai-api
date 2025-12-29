from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Media
from app.routers.routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.clients.microsoft.azure_blob_storage_client import AzureBlobStorageClient
from app.schemas.media_schema import (
    CreateMediaSchema,
    MediaSchema,
    UpdateMediaSchema,
    parse_form_data_to_media,
)
from app.utils.model_utils import apply_model_update, get_resource_from_db


router = APIRouter()


@router.post("/", response_model=MediaSchema)
async def create_media(
    media_file: UploadFile = File(...),
    request: CreateMediaSchema = Depends(parse_form_data_to_media),
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
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


@router.patch("/{media_id}", response_model=MediaSchema)
async def update_media(
    media_id: int,
    request: UpdateMediaSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    media = await get_resource_from_db(Media, media_id, db, company_id)

    apply_model_update(media, request)
    db.commit()
    db.refresh(media)
    return media


@router.delete("/{media_id}")
async def delete_media(
    media_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    azure_blob_storage_client = AzureBlobStorageClient()
    media = await get_resource_from_db(Media, media_id, db, company_id)

    if azure_blob_storage_client.delete_file(media.media_name):
        db.delete(media)
        db.commit()
        return True
    return False
