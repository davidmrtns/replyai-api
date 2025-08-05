from sqlalchemy.orm import Session

from app.db.new_models import Company
from app.services.agenda_service import create_agenda_client
from app.services.crm_service import create_crm_client
from app.services.message_service import create_message_client
from app.types.types import CompanyData


async def get_company(slug: str, token: str, db: Session) -> CompanyData:
    company = db.query(Company).filter_by(slug=slug, token=token, is_active=True).first()

    if company is not None:
        message_client = create_message_client(company, db)
        agenda_client = create_agenda_client(company, db)
        crm_client = create_crm_client(company, db)
        return company, message_client, agenda_client, crm_client
    return None
