from typing import Optional
from app.schemas.base import OrmBaseModel, StrictBaseModel


class AgendaSchema(OrmBaseModel):
    address: str
    shortcut: str


class CreateAgendaSchema(StrictBaseModel):
    address: str
    shortcut: str
    company_id: Optional[int] = None


class UpdateAgendaSchema(StrictBaseModel):
    address: Optional[str] = None
    shortcut: Optional[str] = None
    company_id: Optional[int] = None


class UpdateTimezoneSchema(StrictBaseModel):
    timezone: Optional[str] = None
