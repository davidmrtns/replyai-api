from sqlalchemy.orm import Session

from app.db.models import Agenda, Departamento
from app.db.new_models import Assistant, Company, DigisacClient
from app.clients.assistants_client import AssistantsClient
from app.services.message_service import create_message_client
from app.types.types import AssistantData, CompanyData


async def get_company_data(slug: str, token: str, db: Session) -> CompanyData:
    company = db.query(Company).filter_by(slug=slug, token=token, is_active=True).first()

    if company is not None:
        message_client = create_message_client(company, db)
        return company, message_client
    return None


async def get_agenda(company: Company, shortcut: str, db: Session) -> Agenda | None:
    if company:
        agenda = db.query(Agenda).filter_by(atalho=shortcut, id_empresa=company.id).first()
        return agenda
    return None


async def get_assistant_from_company(
        company: Company,
        purpose: str | None,
        shortcut: str | None,
        db: Session
) -> AssistantData:
    if company:
        if purpose:
            assistant_db = db.query(Assistant).filter_by(company_id=company.id, purpose=purpose).first()
        else:
            assistant_db = db.query(Assistant).filter_by(company_id=company.id, shortcut=shortcut).first()
        if assistant_db:
            assistant = AssistantsClient(assistant_name=assistant_db.assistant_name, openai_assistant_id=assistant_db.openai_assistant_id, openai_api_key=company.openai_api_key)
            return assistant, assistant_db.id
    return None, None


async def get_department(
        company: Company,
        shortcut: str | None,
        is_confirmation_department: bool,
        db: Session
) -> Departamento | None:
    if company:
        digisac_client = db.query(DigisacClient).filter_by(company_id=company.id).first()

        if digisac_client:
            if is_confirmation_department:
                department = db.query(Departamento).filter_by(departamento_confirmacao=True, id_digisac_client=digisac_client.id).first()
            else:
                department = db.query(Departamento).filter_by(atalho=shortcut, id_digisac_client=digisac_client.id).first()
            if department:
                return department
    return None
