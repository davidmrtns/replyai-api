from typing import Optional
from app.schemas.base import StrictBaseModel, OrmBaseModel
from .elevenlabs_client_schema import VoiceSchema


class AssistantSchema(OrmBaseModel):
    assistant_name: str
    instructions: str
    shortcut: str
    voice: Optional[VoiceSchema] = None


class CreateAssistantSchema(StrictBaseModel):
    assistant_name: str
    instructions: str
    shortcut: str
    voice_id: Optional[int] = None
    company_id: Optional[int] = None


class UpdateAssistantSchema(StrictBaseModel):
    assistant_name: Optional[str] = None
    instructions: Optional[str] = None
    shortcut: Optional[str] = None
    voice_id: Optional[int] = None
