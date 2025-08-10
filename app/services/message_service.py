from sqlalchemy.orm import Session

from app.db.models import Midia
from app.db.new_models import Assistant, Company, Contact, DigisacClient, EvolutionAPIClient
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.types.types import MessageData
from app.utils.assistant import Assistant as AiAssistant
from app.utils.digisac import Digisac
from app.utils.eleven_labs import ElevenLabs
from app.utils.evolutionapi import EvolutionAPI
from app.utils.message_client import MessageClient
from app.utils.string_replacements import replace_abbreviations
from app.utils.logger import logger


def create_message_client(company: Company, db: Session) -> MessageClient | None:
    if company.message_client_type == 'digisac':
        digisac_client = db.query(DigisacClient).filter_by(company_id=company.id).first()
        if digisac_client:
            return Digisac(
                slug=digisac_client.digisac_slug,
                service_id=digisac_client.service_id,
                defaultUserId=digisac_client.digisac_default_user,
                token=digisac_client.digisac_token,
                defaultAssistantName=company.default_assistant.assistant_name,
            )
    else:
        evolutionapi_client = db.query(EvolutionAPIClient).filter_by(company_id=company.id).first()
        if evolutionapi_client:
            return EvolutionAPI(
                api_key=evolutionapi_client.api_key,
                instance=evolutionapi_client.instance_name,
                defaultAssistantName=company.default_assistant.assistant_name
            )
    return None


async def get_message(
        request: DigisacRequest | EvolutionAPIRequest,
        message_client: MessageClient,
        assistant: AiAssistant
) -> MessageData:
    message_in_text = None
    is_audio = False
    image = None

    if isinstance(request, DigisacRequest):
        if request.data.message.type == 'audio' or request.data.message.type == 'ptt':
            is_audio = True
        else:
            message_in_text = request.data.message.text or ''
            if request.data.message.type == 'image':
                image = message_client.obter_arquivo(request=request, apenas_url=True)
    elif isinstance(request, EvolutionAPIRequest):
        if request.data.message.audioMessage is not None:
            is_audio = True
        elif request.data.message.imageMessage is not None:
            message_in_text = request.data.message.imageMessage.caption
            image = request.data.message.base64
        else:
            if request.data.message.extendedTextMessage:
                message_in_text = request.data.message.extendedTextMessage.text
            else:
                message_in_text = request.data.message.conversation or ''

    if is_audio:
        file = message_client.obter_arquivo(request=request)
        if file is not None:
            message_in_text = await assistant.transcrever_audio(file)
    return message_in_text, is_audio, image


async def send_message(
        message: str,
        is_audio: bool,
        media_code: str | None,
        contact: Contact,
        company: Company,
        message_client: MessageClient,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        base64_audio_message = None
        mediatype = ''

        if is_audio:
            if isinstance(message_client, Digisac):
                mediatype = 'audio/mpeg'
            else:
                mediatype = 'audio'

            assistant_db = db.query(Assistant).filter_by(assistantId=assistant.id).first()
            if assistant_db:
                voice = assistant_db.voice
                if voice and company.elevenlabs_api_key:
                    elevenlabs_client = ElevenLabs(company.elevenlabs_api_key)
                    message = replace_abbreviations(message)
                    base64_audio_message = await elevenlabs_client.gerar_audio(message, voice.elevenlabs_voice_id, voice.stability,
                                                                               voice.similarity_boost, voice.style)
        
        message_client.enviar_mensagem(message, base64_audio_message, mediatype,
                                    None, contact.contact_id, None, 'bot', assistant.nome)

        if media_code:
            medias = db.query(Midia).filter_by(atalho=media_code, id_empresa=company.id).order_by(Midia.ordem).all()
            for media in medias:
                content = message_client.baixar_arquivo(media.url)
                if content:
                    message_client.enviar_mensagem(mensagem=None, base64=content, mediatype=media.mediatype, nome_arquivo=media.nome,
                                                contact_id=contact.contact_id, userId=None, origin='bot', nome_assistente=assistant.nome)
        return True
    except Exception as e:
        logger.exception(f"Error sending message: {e}")
    return False
