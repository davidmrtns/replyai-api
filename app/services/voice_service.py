import os
import tempfile
from typing import List
from sqlalchemy.orm import Session

from fastapi import UploadFile

from app.clients.elevenlabs_client import ElevenLabsClient
from app.db.models import Company, Voice
from app.exceptions.exceptions import IntegrationException
from app.schemas.elevenlabs_client_schema import (
    CreateVoiceSchema,
    UpdateVoiceSchema,
    VoiceMinSchema,
)
from app.utils.model_utils import apply_model_update, get_resource_from_db


def _get_elevenlabs_client(company_id: int, db: Session):
    company = db.query(Company).filter_by(id=company_id).first()
    return ElevenLabsClient(company.elevenlabs_api_key)


async def create_voice(
    payload: CreateVoiceSchema, files: List[UploadFile], company_id: int, db: Session
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

        elevenlabs_client = _get_elevenlabs_client(company_id, db)

        elvenlabs_voice = elevenlabs_client.add_voice(
            payload.voice_name, payload.description, temp_files
        )
        if elvenlabs_voice.voice_id:
            voice = Voice(
                voice_name=payload.voice_name,
                elevenlabs_voice_id=elvenlabs_voice.voice_id,
                stability=payload.stability,
                similarity_boost=payload.similarity_boost,
                style=payload.style,
                id_empresa=company_id,
            )

            db.add(voice)
            db.commit()
            db.refresh(voice)
            return voice
    except Exception as e:
        raise IntegrationException(
            integration_name="ElevenLabs",
            company_slug="",
            detail="An error occurred while creating the voice.",
            user_friendly_detail="An error occurred while creating the voice. Try again later.",
            status_code=500,
        )
    finally:
        for temp_file in temp_files:
            os.remove(temp_file)


def get_voice(voice_id: int, company_id: int, db: Session):
    voice = get_resource_from_db(Voice, voice_id, db, company_id)
    elevenlabs_client = _get_elevenlabs_client(company_id, db)

    elevenlabs_voice = elevenlabs_client.get_voice(voice.elevenlabs_voice_id)
    if elevenlabs_voice:
        return VoiceMinSchema(
            elevenlabs_voice.preview_url,
            elevenlabs_voice.description,
        )
    return None


def update_voice(
    voice_id: int, request: UpdateVoiceSchema, company_id: int | None, db: Session
):
    voice = get_resource_from_db(Voice, voice_id, db, company_id)
    elevenlabs_client = _get_elevenlabs_client(company_id, db)

    if elevenlabs_client.edit_voice(
        voice.elevenlabs_voice_id, request.voice_name, request.description
    ):
        apply_model_update(voice, request)
        db.commit()
    return voice


def delete_voice(voice_id: int, company_id: int | None, db: Session):
    voice = get_resource_from_db(Voice, voice_id, db, company_id)
    elevenlabs_client = _get_elevenlabs_client(company_id, db)

    if elevenlabs_client.delete_voice(voice.elevenlabs_voice_id):
        db.delete(voice)
        db.commit()
        return True
    return False
