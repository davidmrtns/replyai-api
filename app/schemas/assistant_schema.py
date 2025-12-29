from typing import Optional
from app.db.models import AssistantPurposeEnum
from app.schemas.base import StrictBaseModel, OrmBaseModel
from .elevenlabs_client_schema import VoiceSchema


class AssistantSchema(OrmBaseModel):
    openai_assistant_id: str
    assistant_name: str
    purpose: AssistantPurposeEnum
    shortcut: str
    voice: Optional[VoiceSchema] = None


class CreateAssistantSchema(StrictBaseModel):
    assistant_name: str
    purpose: AssistantPurposeEnum
    instructions: str
    shortcut: str
    voice_id: Optional[int] = None
    company_id: Optional[int] = None


class UpdateAssistantSchema(StrictBaseModel):
    assistant_name: Optional[str] = None
    purpose: Optional[AssistantPurposeEnum] = None
    instructions: Optional[str] = None
    shortcut: Optional[str] = None
    voice_id: Optional[int] = None
