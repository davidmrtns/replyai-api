from datetime import datetime, timedelta

import pytz
from sqlalchemy.orm import Session

from app.db.models import Departamento
from app.db.new_models import Company, Contact, Assistant
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.types.types import CompanyData, ContactAndAssistant
from app.utils.assistant import Assistant as AiAssistant
from app.utils.digisac import Digisac
from app.utils.message_client import MessageClient


async def get_or_create_contact(
        request: DigisacRequest | EvolutionAPIRequest | None,
        company_data: CompanyData,
        db: Session
) -> ContactAndAssistant:
    if isinstance(request, DigisacRequest):
        contact_id = request.data.contactId
    elif isinstance(request, EvolutionAPIRequest):
        contact_id = request.data.key.remoteJid
    else:
        raise ValueError("The request body is invalid")

    company = company_data[0]

    contact = db.query(Contact).filter_by(contact_id=contact_id, company_id=company.id).first()
    timezone = pytz.timezone(company.timezone)

    if contact is None:
        contact = await create_contact(request, contact_id, company_data, timezone, db)
    else:
        now = datetime.now(timezone)
        if not contact.receive_ai_replies:
            last_message_tz = contact.last_message_at.replace(tzinfo=now.tzinfo)
            if contact.last_message_at and (now - last_message_tz >= timedelta(days=1)):
                await change_ai_reply_reception(contact=contact, value=True, db=db)
            else:
                return contact, None
        contact.last_message_at = now
        contact.recall_count = 0
        db.commit()

    if contact.current_assistant:
        assistant_db = db.query(Assistant).filter_by(id=contact.current_assistant, company_id=company.id).first()
    else:
        assistant_db = company.default_assistant
        await update_current_assistant(contact, assistant_db.id, db)
    assistant = AiAssistant(nome=assistant_db.assistant_name, id=assistant_db.openai_assistant_id, api_key=company.openai_api_key)

    return contact, assistant


async def create_contact(
        request: DigisacRequest | EvolutionAPIRequest,
        contact_id: str,
        company_data: CompanyData,
        timezone: pytz.timezone,
        db: Session
) -> Contact:
    company, message_client, _, crm_client = company_data

    contact_data = message_client.obter_dados_contato(request=request)

    deal_id = None
    if crm_client and contact_data:
        deal_id = crm_client.criar_lead(nome_negociacao=contact_data.contact_name,
                                        nome_contato=contact_data.contact_name,
                                        telefone_contato=contact_data.phone_number)

    contact = Contact(
        contact_id=contact_id,
        phone_number=contact_data.phone_number,
        contact_name=contact_data.contact_name,
        last_message_at=datetime.now(timezone),
        deal_id=deal_id,
        company_id=company.id
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return contact


async def change_ai_reply_reception(
        contact: Contact | None,
        contact_id: str | None,
        company: Company | None,
        value: bool,
        db: Session
) -> bool:
    if contact_id:
        contact = db.query(Contact).filter_by(contact_id=contact_id).first()
        if not contact:
            timezone = pytz.timezone(company.timezone)
            await create_contact() # TODO: check correct way of creating contact with reception set to false
            return True

    if contact.receive_ai_replies != value:
        contact.receive_ai_replies = value
        db.commit()
        return True
    return False


'''async def mudar_recebimento_ia(contato: Contact | str, empresa: Company, valor: bool, db: Session):
    if isinstance(contato, str):
        contato_db = db.query(Contact).filter_by(contactId=contato, id_empresa=empresa.id).first()
        if not contato_db:
            timezone = pytz.timezone(empresa.fuso_horario)
            await criar_contato(contato, None, empresa, timezone, valor, db)
            return True
    else:
        contato_db = contato

    if contato_db and contato_db.receber_respostas_ia != valor:
        contato_db.receber_respostas_ia = valor
        db.commit()
        return True
    return False'''


async def change_awaiting_human_contact(
        contact: Contact,
        value: bool,
        db: Session
) -> None:
    contact.awaiting_human_contact = value
    db.commit()


async def transfer_contact(
        message_client: Digisac,
        contact: Contact,
        department: Departamento
) -> None:
    message_client.transferir(
        contactId=contact.contact_id, departmentId=department.departmentId,
        userId=department.userId, byUserId=None, comments=department.comentario
    )


async def update_current_assistant(
        contact: Contact,
        assistant_id: int,
        db: Session
) -> None:
    contact.current_assistant = assistant_id
    db.commit()


async def reset_contact(contact: Contact, db: Session) -> None:
    contact.current_thread_id = None
    contact.current_assistant = None
    contact.last_message_at = None
    contact.recall_count = 0
    contact.under_appointment_confirmation = False
    contact.awaiting_human_contact = False
    db.commit()


async def end_contact(contact: Contact, message_client: MessageClient, db: Session) -> None:
    if isinstance(message_client, Digisac):
        message_client.encerrar_chamado(contactId=contact.contact_id, ticketTopicIds=[], comments='', byUserId=None)
    await reset_contact(contact, db)
