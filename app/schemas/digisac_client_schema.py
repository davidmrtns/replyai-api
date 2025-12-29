from typing import List, Optional
from app.schemas.base import StrictBaseModel, OrmBaseModel


class DepartmentSchema(OrmBaseModel):
    shortcut: str
    contact_transfer_comment: str
    digisac_department_id: str
    digisac_user_id: Optional[str] = None
    is_confirmation_department: bool


class CreateDepartmentSchema(StrictBaseModel):
    shortcut: str
    contact_transfer_comment: str
    digisac_department_id: str
    digisac_user_id: Optional[str] = None
    is_confirmation_department: bool


class UpdateDepartmentSchema(StrictBaseModel):
    shortcut: Optional[str] = None
    contact_transfer_comment: Optional[str] = None
    digisac_department_id: Optional[str] = None
    digisac_user_id: Optional[str] = None
    is_confirmation_department: Optional[bool] = None


class DigisacClientSchema(OrmBaseModel):
    id: int
    digisac_slug: str
    digisac_token: str
    digisac_default_user: Optional[str] = None
    service_id: Optional[str] = None
    departments: List[DepartmentSchema]


class CreateDigisacClientSchema(StrictBaseModel):
    digisac_slug: str
    digisac_token: str
    digisac_default_user: Optional[str] = None
    service_id: Optional[str] = None


class UpdateDigisacClientSchema(StrictBaseModel):
    digisac_slug: Optional[str] = None
    digisac_token: Optional[str] = None
    digisac_default_user: Optional[str] = None
    service_id: Optional[str] = None
