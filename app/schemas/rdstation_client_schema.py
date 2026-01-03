from typing import List, Optional
from app.schemas.base import OrmBaseModel, StrictBaseModel


class CreateRDStationClientSchema(StrictBaseModel):
    token: str
    default_source_id: str
    company_id: Optional[int] = None


class UpdateRDStationClientSchema(StrictBaseModel):
    token: Optional[str] = None
    default_source_id: Optional[str] = None


class DealStageSchema(StrictBaseModel):
    id: int
    shortcut: str
    deal_stage_id: str
    user_id: Optional[str] = None
    is_initial_deal_stage: bool


class CreateDealStageSchema(StrictBaseModel):
    shortcut: str
    deal_stage_id: str
    user_id: Optional[str] = None
    is_initial_deal_stage: bool


class UpdateDealStageSchema(StrictBaseModel):
    shortcut: Optional[str] = None
    deal_stage_id: Optional[str] = None
    user_id: Optional[str] = None
    is_initial_deal_stage: Optional[bool] = None


class RDStationClientSchema(OrmBaseModel):
    id: int
    token: str
    default_source_id: str
    stages: List[DealStageSchema]
