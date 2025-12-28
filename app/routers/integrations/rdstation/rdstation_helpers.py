from sqlalchemy.orm import Session

from app.db.models import RDStationCRMClient, RDStationCRMDealStage
from app.exceptions.exceptions import ResourceNotFoundException
from app.utils.model_utils import get_resource_from_db


async def get_deal_stage_from_db(
    rdstation_client_id: int, deal_stage_id: int, company_id: int | None, db: Session
):
    rdstation_client = await get_resource_from_db(
        RDStationCRMClient, rdstation_client_id, db, company_id
    )

    query = db.query(RDStationCRMDealStage).filter_by(
        id=deal_stage_id, id_rdstationcrm_client=rdstation_client.id
    )
    if company_id:
        query = query.join(RDStationCRMClient).filter_by(company_id=company_id)

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
