from sqlalchemy.orm import Session

from app.db.new_models import RDStationCRMClient, RDStationCRMDealStage
from app.db.new_models import Company, Contact
from app.utils.crm_client import CRMClient
from app.utils.rdstation_crm import RDStationCRM


def create_crm_client(company: Company, db: Session) -> CRMClient | None:
    if company.crm_client_type == "rdstation":
        rdstationcrm_client = db.query(RDStationCRMClient).filter_by(company_id=company.id).first()
        if rdstationcrm_client:
            initial_deal_stage = db.query(RDStationCRMDealStage).filter_by(is_initial_deal_stage=True, rdstationcrm_client_id=rdstationcrm_client.id).first()
            if initial_deal_stage:
                return RDStationCRM(
                    token=rdstationcrm_client.token,
                    user_id=initial_deal_stage.user_id,
                    deal_stage_id=initial_deal_stage.deal_stage_id,
                    deal_source_id=rdstationcrm_client.default_source_id
                )
    return None


# TODO: after removing the events pipelines, this function is not being used anymore; improve and start using it
async def mover_lead(crm_client: CRMClient, contato: Contact, empresa: Company, atalho: str, db: Session):
    if crm_client and contato.deal_id:
        deal_stage_db = (
            db.query(RDStationCRMDealStage)
            .join(RDStationCRMClient, RDStationCRMDealStage.id_rdstationcrm_client == RDStationCRMClient.id)
            .filter(
                RDStationCRMDealStage.atalho == atalho,
                RDStationCRMClient.id_empresa == empresa.id
            )
            .first()
        )

        if deal_stage_db:
            return crm_client.mudar_etapa(deal_id=contato.deal_id,
                                          deal_stage_id=deal_stage_db.deal_stage_id,
                                          user_id=deal_stage_db.user_id)