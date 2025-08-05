from app.db.new_models import Company, Contact
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.services.contato_service import mudar_recebimento_ia, redefinir_contato
from app.utils.evolutionapi import EvolutionAPI
from app.utils.message_client import MessageClient


async def _handle_evolutionapi_request(
        request: EvolutionAPIRequest,
        company: Company,
        message_client: MessageClient,
        is_audio: bool,
        db
) -> bool:
    if request.data.key.fromMe:
        if company:
            await mudar_recebimento_ia(request.data.key.remoteJid, company, False, db)
        return False
    if isinstance(message_client, EvolutionAPI):
        message_client.enviar_presenca(request.data.key.remoteJid, is_audio)
    return True


async def _handle_digisac_request(
        request: DigisacRequest,
        contact: Contact,
        db
) -> bool:
    if request.data.command == 'reset':
        await redefinir_contato(contact, db)
        return False
    return True


async def _handle_contact_can_receive_replies(
        contact: Contact
) -> bool:
    return contact.receive_ai_replies
