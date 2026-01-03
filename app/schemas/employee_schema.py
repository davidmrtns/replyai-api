from typing import Optional
from app.schemas.base import OrmBaseModel, StrictBaseModel


class EmployeeSchema(OrmBaseModel):
    name: str
    nickname: str
    department_name: str


class CreateEmployeeSchema(StrictBaseModel):
    name: str
    nickname: str
    department_name: str
    company_id: Optional[int] = None


class UpdateEmployeeSchema(StrictBaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    department_name: Optional[str] = None
