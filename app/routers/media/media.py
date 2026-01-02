from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.routers.routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.media_schema import (
    CreateMediaSchema,
    MediaSchema,
    UpdateMediaSchema,
    parse_form_data_to_media,
)
from app.services.media_service import (
    create_media as create_media_service,
    update_media as update_media_service,
    delete_media as delete_media_service,
)


router = APIRouter()


@router.post("/", response_model=MediaSchema)
async def create_media(
    media_file: UploadFile = File(...),
    request: CreateMediaSchema = Depends(parse_form_data_to_media),
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_media_service(media_file, request, company_id, db)


@router.patch("/{media_id}", response_model=MediaSchema)
async def update_media(
    media_id: int,
    request: UpdateMediaSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_media_service(media_id, request, company_id, db)


@router.delete("/{media_id}")
async def delete_media(
    media_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_media_service(media_id, company_id, db)
