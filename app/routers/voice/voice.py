import os
import tempfile
from typing import List
from fastapi import APIRouter, UploadFile
from fastapi.params import Depends, File
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Voice
from app.exceptions.exceptions import IntegrationAuthException
from app.schemas.elevenlabs_client_schema import (
    CreateVoiceSchema,
    UpdateVoiceSchema,
    VoiceMinSchema,
    VoiceSchema,
    parse_form_data_to_voice,
)
from app.utils.model_utils import apply_model_update, get_resource_from_db
from ..routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from .voice_helpers import get_elevenlabs_client


router = APIRouter()


@router.post("/", response_model=VoiceSchema)
async def create_voice(
    request: CreateVoiceSchema = Depends(parse_form_data_to_voice),
    files: List[UploadFile] = File(...),
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    temp_files = []

    try:
        for file in files:
            temp = tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(file.filename)[1]
            )
            temp.write(await file.read())
            temp.close()
            temp_files.append(temp.name)

        elevenlabs_client = get_elevenlabs_client(company_id, db)

        elvenlabs_voice = elevenlabs_client.add_voice(
            request.voice_name, request.description, temp_files
        )
        if elvenlabs_voice.voice_id:
            voice = Voice(
                voice_name=request.voice_name,
                elevenlabs_voice_id=elvenlabs_voice.voice_id,
                stability=request.stability,
                similarity_boost=request.similarity_boost,
                style=request.style,
                id_empresa=company_id,
            )

            db.add(voice)
            db.commit()
            db.refresh(voice)
            return voice
    except Exception as e:
        # TODO: raise custom exception
        print(e)
        raise IntegrationAuthException(
            integration_name="ElevenLabs",
            company_slug="",
            detail="An error occurred while creating the voice.",
            user_friendly_detail="An error occurred while creating the voice. Try again later.",
            status_code=500,
        )
    finally:
        for temp_file in temp_files:
            os.remove(temp_file)


@router.get("/{voice_id}", response_model=VoiceMinSchema)
async def get_voice(
    voice_id: int,
    company_id: int = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    voice = await get_resource_from_db(Voice, voice_id, db, company_id)
    elevenlabs_client = get_elevenlabs_client(company_id, db)

    elevenlabs_voice = elevenlabs_client.get_voice(voice.elevenlabs_voice_id)
    if elevenlabs_voice:
        return VoiceMinSchema(
            elevenlabs_voice.preview_url,
            elevenlabs_voice.description,
        )
    return None


@router.patch("/{voice_id}", response_model=VoiceSchema)
async def update_voice(
    voice_id: int,
    request: UpdateVoiceSchema,
    company_id: int = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    voice = await get_resource_from_db(Voice, voice_id, db, company_id)
    elevenlabs_client = get_elevenlabs_client(company_id, db)

    if elevenlabs_client.edit_voice(
        voice.elevenlabs_voice_id, request.voice_name, request.description
    ):
        apply_model_update(voice, request)
        db.commit()
    return voice


@router.delete("/{voice_id}")
async def delete_voice(
    voice_id: int,
    company_id: int = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    voice = await get_resource_from_db(Voice, voice_id, db, company_id)
    elevenlabs_client = get_elevenlabs_client(company_id, db)

    if elevenlabs_client.delete_voice(voice.elevenlabs_voice_id):
        db.delete(voice)
        db.commit()
        return True
    return False
