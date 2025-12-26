from app.clients.message_client import MessageClient
from app.db.new_models import Company, Contact
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.services.contact_service import change_ai_reply_reception, reset_contact
from app.clients.evolutionapi_client import EvolutionAPIClient


async def _handle_evolutionapi_request(
    request: EvolutionAPIRequest,
    company: Company,
    message_client: MessageClient,
    is_audio: bool,
    db,
) -> bool:
    if request.data.key.fromMe:
        if company:
            await change_ai_reply_reception(
                contact_id=request.data.key.remoteJid,
                company=company,
                value=False,
                db=db,
            )
        return False
    if isinstance(message_client, EvolutionAPIClient):
        presence_type = "recording" if is_audio else "composing"
        message_client.send_presence(request.data.key.remoteJid, presence_type)
    return True


async def _handle_digisac_request(
    request: DigisacRequest, contact: Contact, db
) -> bool:
    if request.data.command == "reset":
        await reset_contact(contact, db)
        return False
    return True


async def _handle_contact_can_receive_replies(contact: Contact) -> bool:
    return contact.receive_ai_replies
