from sqlalchemy.orm import Session

from app.db.models import Empresa
from app.services.agendamento_service import criar_agenda_client
from app.services.crm_service import criar_crm_client
from app.services.mensagem_service import criar_message_client
from app.types.types import CompanyData


async def get_company(slug: str, token: str, db: Session) -> CompanyData:
    company = db.query(Empresa).filter_by(slug=slug, token=token, empresa_ativa=True).first()

    if company is not None:
        message_client = criar_message_client(company, db)
        agenda_client = criar_agenda_client(company, db)
        crm_client = criar_crm_client(company, db)
        return company, message_client, agenda_client, crm_client
    return None
