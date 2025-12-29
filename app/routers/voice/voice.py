import os
import tempfile
from typing import List
from fastapi import APIRouter, UploadFile
from fastapi.params import Depends, File
from sqlalchemy.orm import Session
from typing import Annotated

from app.db.database import obter_sessao
from app.db.models import Company, Voice
from app.schemas.elevenlabs_client_schema import (
    CreateVoiceSchema,
    UpdateVoiceSchema,
    VoiceMinSchema,
    VoiceSchema,
    parse_form_data_to_voice,
)
from ..routers_helpers import check_company_access
from .voice_helpers import get_elevenlabs_client, get_voice_from_db


router = APIRouter()


@router.post("/{company_slug}", response_model=VoiceSchema)
async def create_voice(
    company_slug: str,
    company: Annotated[Company, Depends(check_company_access)],
    request: CreateVoiceSchema = Depends(parse_form_data_to_voice),
    files: List[UploadFile] = File(...),
    db: Session = Depends(obter_sessao),
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

        elevenlabs_client = get_elevenlabs_client(company)

        voice = elevenlabs_client.add_voice(request.nome, request.descricao, temp_files)
        if voice.voice_id:
            voz_db = Voice(
                nome=request.nome,
                voiceId=voice.voice_id,
                stability=request.stability,
                similarity_boost=request.similarity_boost,
                style=request.style,
                id_empresa=company.id,
            )

            db.add(voz_db)
            db.commit()
            db.refresh(voz_db)
            return voz_db
    except Exception as e:
        # TODO: raise custom exception
        print(e)
        return {"error": "Error while creating voice"}
    finally:
        for temp_file in temp_files:
            os.remove(temp_file)


@router.get("/{company_slug}/{voice_id}", response_model=VoiceMinSchema)
async def get_voice(
    slug: str,
    voice_id: int,
    company: Annotated[Company, Depends(check_company_access)],
    db: Session = Depends(obter_sessao),
):
    voice_db = get_voice_from_db(company.id, voice_id, db)
    elevenlabs_client = get_elevenlabs_client(company)

    voice = elevenlabs_client.get_voice(voice_db.elevenlabs_voice_id)
    if voice:
        return VoiceMinSchema(
            voice.preview_url,
            voice.description,
        )
    return None


@router.patch("/{company_slug}/{voice_id}", response_model=VoiceSchema)
async def edit_voice(
    company_slug: str,
    voice_id: int,
    request: UpdateVoiceSchema,
    company: Annotated[Company, Depends(check_company_access)],
    db: Session = Depends(obter_sessao),
):
    voice_db = get_voice_from_db(company.id, voice_id, db)
    elevenlabs_client = get_elevenlabs_client(company)

    response = elevenlabs_client.edit_voice(
        voice_db.elevenlabs_voice_id, request.nome, request.descricao
    )

    if response:
        voice_db.voice_name = request.nome
        voice_db.stability = request.stability
        voice_db.similarity_boost = request.similarity_boost
        voice_db.style = request.style

        db.commit()
        return voice_db
    return None


@router.delete("/{company_slug}/{voice_id}")
async def delete_voice(
    company_slug: str,
    voice_id: int,
    company: Annotated[Company, Depends(check_company_access)],
    db: Session = Depends(obter_sessao),
):
    voice_db = get_voice_from_db(company.id, voice_id, db)
    elevenlabs_client = get_elevenlabs_client(company)

    if elevenlabs_client.delete_voice(voice_db.elevenlabs_voice_id):
        db.delete(voice_db)
        db.commit()
        return True
    return False
