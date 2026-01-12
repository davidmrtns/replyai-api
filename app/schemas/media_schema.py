from typing import Optional

from fastapi import Form
from app.schemas.base import OrmBaseModel, StrictBaseModel


class MediaSchema(OrmBaseModel):
    id: int
    url: str
    mediatype: str
    media_name: str
    shortcut: str
    order: int


class CreateMediaSchema(StrictBaseModel):
    shortcut: str
    order: int
    company_id: Optional[int] = None


class UpdateMediaSchema(StrictBaseModel):
    shortcut: Optional[str] = None
    order: Optional[int] = None


def parse_form_data_to_media(
    shortcut: str = Form(...), order: int = Form(...)
) -> CreateMediaSchema:
    return CreateMediaSchema(shortcut=shortcut, order=order)
