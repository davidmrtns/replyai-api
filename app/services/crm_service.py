from sqlalchemy.orm import Session

from app.clients.crm_client import CRMClient
from app.clients.rdstation_client import RDStationClient
from app.db.models import RDStationClient as RDStationClientDB, RDStationDealStage
from app.db.models import Company, Contact


# TODO: move to utility file
def create_crm_client(company: Company, db: Session) -> CRMClient | None:
    if company.crm_client_type == "rdstation":
        rdstationcrm_client = (
            db.query(RDStationClientDB).filter_by(company_id=company.id).first()
        )
        if rdstationcrm_client:
            initial_deal_stage = (
                db.query(RDStationDealStage)
                .filter_by(
                    is_initial_deal_stage=True,
                    rdstationcrm_client_id=rdstationcrm_client.id,
                )
                .first()
            )
            if initial_deal_stage:
                return RDStationClient(
                    rdstationcrm_client.token,
                    initial_deal_stage.deal_stage_id,
                    rdstationcrm_client.default_source_id,
                    initial_deal_stage.user_id,
                )
    return None


# TODO: turn into an assistant function
async def move_lead(
    crm_client: CRMClient,
    contact: Contact,
    company: Company,
    deal_stage_shortcut: str,
    db: Session,
) -> bool:
    status = False

    if crm_client and contact.deal_id:
        deal_stage_db = (
            db.query(RDStationDealStage)
            .join(
                RDStationClientDB,
                RDStationDealStage.rdstationcrm_client_id == RDStationClientDB.id,
            )
            .filter(
                RDStationDealStage.shortcut == deal_stage_shortcut,
                RDStationClientDB.company_id == company.id,
            )
            .first()
        )

        if deal_stage_db:
            crm_client.change_stage(
                deal_id=contact.deal_id,
                deal_stage_id=deal_stage_db.deal_stage_id,
                user_id=deal_stage_db.user_id,
            )
            status = True

    return status
