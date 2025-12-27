from sqlalchemy.orm import Session

from app.db.models import RDStationCRMClient, RDStationCRMDealStage, User
from app.exceptions.exceptions import ResourceNotFoundException


async def get_rdstation_client_from_db(
    rdstation_client_id: int, logged_in_user: User, db: Session
):
    query = db.query(RDStationCRMClient).filter_by(id=rdstation_client_id)
    if logged_in_user.company_id:
        query = query.filter_by(company_id=logged_in_user.company_id)

    rdstation_client = query.first()

    if not rdstation_client:
        raise ResourceNotFoundException(
            resource_type="RDStation client",
            resource_id=rdstation_client_id,
            detail="RDStation client not found for the specified company and ID.",
            user_friendly_detail="RDStation client not found.",
            http_status_code=404,
        )
    return rdstation_client


async def get_deal_stage_from_db(
    rdstation_client_id: int, deal_stage_id: int, logged_in_user: User, db: Session
):
    rdstation_client = await get_rdstation_client_from_db(
        rdstation_client_id, logged_in_user, db
    )

    query = db.query(RDStationCRMDealStage).filter_by(
        id=deal_stage_id, id_rdstationcrm_client=rdstation_client.id
    )
    if logged_in_user.company_id:
        query = query.join(RDStationCRMClient).filter_by(
            company_id=logged_in_user.company_id
        )

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
