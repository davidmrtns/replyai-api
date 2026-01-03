from typing import Optional
from app.schemas.base import OrmBaseModel


class OutlookClientSchema(OrmBaseModel):
    id: Optional[int] = None
    default_user: str
    timezone: str
