from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import obter_sessao
from app.db.models import RDStationCRMClient, RDStationCRMDealStage
from app.exceptions.exceptions import ConflictingRequestException
from app.utils.model_utils import apply_model_update, get_resource_from_db
from .rdstation_helpers import get_deal_stage_from_db
from app.routers.routers_helpers import (
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
from app.utils.api_key_encryption import encrypt_api_key


router = APIRouter()


# TODO: maybe add a GET endpoint to get rdstation client


@router.post("/", response_model=RDStationClientSchema)
async def create_rdstation_client(
    request: CreateRDStationClientSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(obter_sessao),
):
    rdstationcrm_client = (
        db.query(RDStationCRMClient).filter_by(company_id=company_id).first()
    )
    if rdstationcrm_client:
        raise ConflictingRequestException(
            detail="The company already has an RD Station client with this client number. Try again with a different client number.",
            user_friendly_detail="This company already has an RD Station client with this client number.",
            http_status_code=409,
        )

    rdstationcrm_client = RDStationCRMClient(
        token=encrypt_api_key(request.token),
        default_source_id=request.default_source_id,
        company_id=company_id,
    )

    db.add(rdstationcrm_client)
    db.commit()
    db.refresh(rdstationcrm_client)
    return rdstationcrm_client


@router.patch("/{rdstation_client_id}", response_model=RDStationClientSchema)
async def update_rdstation_client(
    rdstation_client_id: int,
    request: UpdateRDStationClientSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    update_data = request.model_dump(exclude_unset=True)

    if "token" in update_data:
        update_data["token"] = encrypt_api_key(update_data["token"])

    rdstation_client = await get_resource_from_db(
        RDStationCRMClient, rdstation_client_id, db, company_id
    )

    apply_model_update(rdstation_client, update_data)
    db.commit()
    return rdstation_client


@router.delete("/{rdstation_client_id}")
async def delete_rdstation_client(
    rdstation_client_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    rdstation_client = await get_resource_from_db(
        RDStationCRMClient, rdstation_client_id, db, company_id
    )
    if rdstation_client:
        # TODO: check if there are dependent deal stages before deleting
        db.delete(rdstation_client)
        db.commit()
        return True
    return False


@router.post("/{rdstation_client_id}/stage", response_model=DealStageSchema)
async def create_deal_stage(
    rdstation_client_id: int,
    request: CreateDealStageSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    rdstation_client = await get_resource_from_db(
        RDStationCRMClient, rdstation_client_id, db, company_id
    )

    deal_stage = RDStationCRMDealStage(
        shortcut=request.shortcut,
        deal_stage_id=request.deal_stage_id,
        user_id=request.user_id,
        is_initial_deal_stage=request.is_initial_deal_stage,
        id_rdstationcrm_client=rdstation_client.id,
    )

    db.add(deal_stage)
    db.commit()
    db.refresh(deal_stage)
    return deal_stage


@router.patch(
    "/{rdstation_client_id}/stage/{deal_stage_id}",
    response_model=DealStageSchema,
)
async def update_deal_stage(
    rdstation_client_id: int,
    deal_stage_id: int,
    request: UpdateDealStageSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    deal_stage = await get_deal_stage_from_db(
        rdstation_client_id, deal_stage_id, company_id, db
    )

    apply_model_update(deal_stage, request)
    db.commit()
    return deal_stage


@router.delete("/{rdstation_client_id}/stage/{deal_stage_id}")
async def delete_deal_stage(
    rdstation_client_id: int,
    deal_stage_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    deal_stage = await get_deal_stage_from_db(
        rdstation_client_id, deal_stage_id, company_id, db
    )
    if deal_stage:
        db.delete(deal_stage)
        db.commit()
        return True
    return False
