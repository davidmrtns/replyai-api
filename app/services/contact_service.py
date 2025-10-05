from datetime import datetime, timedelta

import pytz
from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.db.models import Departamento
from app.db.new_models import Company, Contact, Assistant
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.services.crm_service import create_crm_client
from app.types.types import CompanyData, ContactAndAssistant
from app.clients.assistants_client import AssistantsClient
from app.clients.message_client import MessageClient


# TODO: refactor to improve redability and maintainability
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
    assistant = AssistantsClient(assistant_name=assistant_db.assistant_name, openai_assistant_id=assistant_db.openai_assistant_id, openai_api_key=company.openai_api_key)

    return contact, assistant


async def create_contact(
        request: DigisacRequest | EvolutionAPIRequest,
        contact_id: str,
        company_data: CompanyData,
        timezone: pytz.timezone,
        db: Session
) -> Contact:
    company, message_client = company_data

    contact_data = message_client.get_contact_data(request=request)

    deal_id = None
    crm_client = create_crm_client(company, db)
    if crm_client and contact_data:
        deal_id = crm_client.create_lead(contact_data.contact_name, contact_data.contact_name, contact_data.phone_number)

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


async def change_awaiting_human_contact(
        contact: Contact,
        value: bool,
        db: Session
) -> None:
    contact.awaiting_human_contact = value
    db.commit()


async def transfer_contact(
        message_client: DigisacClient,
        contact: Contact,
        department: Departamento
) -> None:
    message_client.transfer_contact(
        contact.contact_id,
        department.departmentId,
        department.userId,
        byUserId=None,
        comments=department.comentario
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
    if isinstance(message_client, DigisacClient):
        message_client.close_contact_ticket(
            contact.contact_id,
            ticket_topic_ids=[],
            comments='',
            by_user_id=None
        )
    await reset_contact(contact, db)
