from typing import Optional
from app.schemas.base import OrmBaseModel, StrictBaseModel


class AsaasClientSchema(OrmBaseModel):
    id: int
    token: str
    label: str
    client_number: int


class CreateAsaasClientSchema(StrictBaseModel):
    token: str
    label: str
    client_number: int
    company_id: Optional[int] = None


class UpdateAsaasClientSchema(StrictBaseModel):
    token: Optional[str] = None
    label: Optional[str] = None
    client_number: Optional[int] = None
