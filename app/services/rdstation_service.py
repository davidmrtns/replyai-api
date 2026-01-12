from sqlalchemy.orm import Session

from app.db.models import (
    RDStationClient as RDStationClientDB,
    RDStationDealStage,
)
from app.exceptions.exceptions import (
    ConflictingRequestException,
    ResourceNotFoundException,
)
from app.schemas.rdstation_client_schema import (
    CreateDealStageSchema,
    CreateRDStationClientSchema,
    UpdateDealStageSchema,
    UpdateRDStationClientSchema,
)
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


def _get_deal_stage_from_db(
    rdstation_client_id: int, deal_stage_id: int, company_id: int | None, db: Session
):
    rdstation_client = get_resource_from_db(
        RDStationClientDB, rdstation_client_id, db, company_id
    )

    query = db.query(RDStationDealStage).filter_by(
        id=deal_stage_id, id_rdstationcrm_client=rdstation_client.id
    )
    if company_id:
        query = query.join(RDStationClientDB).filter_by(company_id=company_id)

    deal_stage = query.first()

    if not deal_stage:
        raise ResourceNotFoundException(
            resource_type="RDStation Deal Stage",
            resource_id=deal_stage_id,
            detail="Deal Stage not found for the specified RDStation client and ID.",
            user_friendly_detail="Deal Stage not found.",
            http_status_code=404,
        )
    return deal_stage


def create_rdstation_client(
    payload: CreateRDStationClientSchema, company_id: int, db: Session
):
    rdstationcrm_client = (
        db.query(RDStationClientDB).filter_by(company_id=company_id).first()
    )
    if rdstationcrm_client:
        raise ConflictingRequestException(
            detail="The company already has an RD Station client with this client number. Try again with a different client number.",
            user_friendly_detail="This company already has an RD Station client with this client number.",
            http_status_code=409,
        )

    rdstationcrm_client = RDStationClientDB(
        token=encrypt_api_key(payload.token),
        default_source_id=payload.default_source_id,
        company_id=company_id,
    )

    db.add(rdstationcrm_client)
    db.commit()
    db.refresh(rdstationcrm_client)
    return rdstationcrm_client


def update_rdstation_client(
    rdstation_client_id: int,
    payload: UpdateRDStationClientSchema,
    company_id: int | None,
    db: Session,
):
    update_data = payload.model_dump(exclude_unset=True)

    if "token" in update_data:
        update_data["token"] = encrypt_api_key(update_data["token"])

    rdstation_client = get_resource_from_db(
        RDStationClientDB, rdstation_client_id, db, company_id
    )

    apply_model_update(rdstation_client, update_data)
    db.commit()
    return rdstation_client


def delete_rdstation_client(
    rdstation_client_id: int, company_id: int | None, db: Session
):
    rdstation_client = get_resource_from_db(
        RDStationClientDB, rdstation_client_id, db, company_id
    )
    if rdstation_client:
        db.delete(rdstation_client)
        db.commit()
        return True
    return False


def create_deal_stage(
    rdstation_client_id: int,
    payload: CreateDealStageSchema,
    company_id: int | None,
    db: Session,
):
    rdstation_client = get_resource_from_db(
        RDStationClientDB, rdstation_client_id, db, company_id
    )

    deal_stage = RDStationDealStage(
        shortcut=payload.shortcut,
        deal_stage_id=payload.deal_stage_id,
        user_id=payload.user_id,
        is_initial_deal_stage=payload.is_initial_deal_stage,
        id_rdstationcrm_client=rdstation_client.id,
    )

    db.add(deal_stage)
    db.commit()
    db.refresh(deal_stage)
    return deal_stage


def update_deal_stage(
    rdstation_client_id: int,
    deal_stage_id: int,
    payload: UpdateDealStageSchema,
    company_id: int | None,
    db: Session,
):
    deal_stage = _get_deal_stage_from_db(
        rdstation_client_id, deal_stage_id, company_id, db
    )

    apply_model_update(deal_stage, payload)
    db.commit()
    return deal_stage


def delete_deal_stage(
    rdstation_client_id: int,
    deal_stage_id: int,
    company_id: int | None,
    db: Session,
):
    deal_stage = _get_deal_stage_from_db(
        rdstation_client_id, deal_stage_id, company_id, db
    )
    if deal_stage:
        db.delete(deal_stage)
        db.commit()
        return True
    return False
