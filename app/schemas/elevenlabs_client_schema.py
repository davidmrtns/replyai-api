from typing import Optional

from fastapi import Form
from app.schemas.base import OrmBaseModel, StrictBaseModel


class VoiceSchema(OrmBaseModel):
    id: int
    voice_name: str
    elevenlabs_voice_id: str
    stability: float
    similarity_boost: float
    style: float


class VoiceMinSchema(OrmBaseModel):
    preview_url: str
    description: str


class CreateVoiceSchema(StrictBaseModel):
    voice_name: str
    description: str
    stability: float
    similarity_boost: float
    style: float
    company_id: Optional[int] = None


class UpdateVoiceSchema(StrictBaseModel):
    voice_name: Optional[str] = None
    description: Optional[str] = None
    stability: Optional[float] = None
    similarity_boost: Optional[float] = None
    style: Optional[float] = None


def parse_form_data_to_voice(
    voice_name: str = Form(...),
    description: Optional[str] = Form(None),
    stability: float = Form(...),
    similarity_boost: float = Form(...),
    style: float = Form(...),
) -> VoiceSchema:
    return VoiceSchema(
        voice_name=voice_name,
        description=description,
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
    )
