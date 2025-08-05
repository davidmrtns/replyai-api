from datetime import datetime, timedelta

import pytz
from sqlalchemy.orm import Session

from app.db.new_models import Contact, Assistant
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.types.types import CompanyData, ContactAndAssistant
from app.utils.assistant import Assistant as AiAssistant


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
                await change_ai_reply_reception(contact, True, db)
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
        contact: Contact,
        value: bool,
        db: Session
) -> bool:
    if contact.receive_ai_replies != value:
        contact.receive_ai_replies = value
        db.commit()
        return True
    return False


async def update_current_assistant(
        contact: Contact,
        assistant_id: int,
        db: Session
) -> None:
    contact.current_assistant = assistant_id
    db.commit()
