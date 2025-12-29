from typing import Optional
from app.schemas.base import OrmBaseModel


class GoogleCalendarSchema(OrmBaseModel):
    id: Optional[int] = None
    client_email: str
    timezone: str
