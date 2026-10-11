from typing import Optional

from app.db.models import AIProviderNamesEnum
from app.schemas.base import OrmBaseModel, StrictBaseModel


class AIProviderSchema(OrmBaseModel):
    id: int
    provider_name: AIProviderNamesEnum
    api_key: str
    company_id: int


class CreateAIProviderSchema(StrictBaseModel):
    provider_name: AIProviderNamesEnum
    api_key: str
    company_id: Optional[int] = None


class UpdateAIProviderSchema(StrictBaseModel):
    provider_name: Optional[AIProviderNamesEnum] = None
    api_key: Optional[str] = None
