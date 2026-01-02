from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import get_db_session
from ..routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.rdstation_client_schema import (
    CreateDealStageSchema,
    CreateRDStationClientSchema,
    DealStageSchema,
    RDStationClientSchema,
    UpdateDealStageSchema,
    UpdateRDStationClientSchema,
)
from app.services.rdstation_service import (
    create_rdstation_client as create_rdstation_client_service,
    update_rdstation_client as update_rdstation_client_service,
    delete_rdstation_client as delete_rdstation_client_service,
    create_deal_stage as create_deal_stage_service,
    update_deal_stage as update_deal_stage_service,
    delete_deal_stage as delete_deal_stage_service,
)


router = APIRouter()


# TODO: maybe add a GET endpoint to get rdstation client


@router.post("/", response_model=RDStationClientSchema)
async def create_rdstation_client(
    request: CreateRDStationClientSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_rdstation_client_service(request, company_id, db)


@router.patch("/{rdstation_client_id}", response_model=RDStationClientSchema)
async def update_rdstation_client(
    rdstation_client_id: int,
    request: UpdateRDStationClientSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_rdstation_client_service(
        rdstation_client_id, request, company_id, db
    )


@router.delete("/{rdstation_client_id}")
async def delete_rdstation_client(
    rdstation_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_rdstation_client_service(rdstation_client_id, company_id, db)


@router.post("/{rdstation_client_id}/stage", response_model=DealStageSchema)
async def create_deal_stage(
    rdstation_client_id: int,
    request: CreateDealStageSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await create_deal_stage_service(rdstation_client_id, request, company_id, db)


@router.patch(
    "/{rdstation_client_id}/stage/{deal_stage_id}",
    response_model=DealStageSchema,
)
async def update_deal_stage(
    rdstation_client_id: int,
    deal_stage_id: int,
    request: UpdateDealStageSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_deal_stage_service(
        rdstation_client_id, deal_stage_id, request, company_id, db
    )


@router.delete("/{rdstation_client_id}/stage/{deal_stage_id}")
async def delete_deal_stage(
    rdstation_client_id: int,
    deal_stage_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_deal_stage_service(
        rdstation_client_id, deal_stage_id, company_id, db
    )
