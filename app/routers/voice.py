from typing import List
from fastapi import APIRouter, UploadFile
from fastapi.params import Depends, File
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.elevenlabs_client_schema import (
    CreateVoiceSchema,
    UpdateVoiceSchema,
    VoiceMinSchema,
    VoiceSchema,
    parse_form_data_to_voice,
)
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.services.voice_service import (
    create_voice as create_voice_service,
    get_voice as get_voice_service,
    get_voice as get_voice_service,
    update_voice as update_voice_service,
    delete_voice as delete_voice_service,
)


router = APIRouter()


@router.post("/", response_model=VoiceSchema)
async def create_voice(
    request: CreateVoiceSchema = Depends(parse_form_data_to_voice),
    files: List[UploadFile] = File(...),
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_voice_service(request, files, company_id, db)


@router.get("/{voice_id}", response_model=VoiceMinSchema)
def get_voice(
    voice_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return get_voice_service(voice_id, company_id, db)


@router.patch("/{voice_id}", response_model=VoiceSchema)
def update_voice(
    voice_id: int,
    request: UpdateVoiceSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return update_voice_service(voice_id, request, company_id, db)


@router.delete("/{voice_id}")
def delete_voice(
    voice_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return delete_voice_service(voice_id, company_id, db)
