from app.db.models import Empresa, Contato
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.services.contato_service import mudar_recebimento_ia, redefinir_contato
from app.utils.evolutionapi import EvolutionAPI


async def _handle_evolutionapi_request(
        request: EvolutionAPIRequest,
        company: Empresa,
        message_client: EvolutionAPI,
        is_audio: bool,
        db
) -> bool:
    if request.data.key.fromMe:
        if company:
            await mudar_recebimento_ia(request.data.key.remoteJid, company, False, db)
        return False
    message_client.enviar_presenca(request.data.key.remoteJid, is_audio)
    return True


async def _handle_digisac_request(
        request: DigisacRequest,
        contact: Contato,
        db
) -> bool:
    if request.data.command == 'reset':
        await redefinir_contato(contact, db)
        return False
    return True


async def _handle_contact_can_receive_replies(
        contact: Contato
) -> bool:
    return contact.receber_respostas_ia
