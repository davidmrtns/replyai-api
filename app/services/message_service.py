from typing import Literal
from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.clients.evolutionapi_client import EvolutionAPIClient
from app.db.models import (
    Assistant,
    Company,
    Contact,
    Media,
    DigisacClient as DigisacClientDB,
    EvolutionAPIClient as EvolutionAPIClientDB,
)
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.types.types import MessageData
from app.utils.download_file import download_file
from app.clients.assistants_client import AssistantsClient
from app.clients.elevenlabs_client import ElevenLabsClient
from app.clients.message_client import MediaMessageData, MessageClient
from app.utils.string_replacements import replace_abbreviations


def create_message_client(company: Company, db: Session) -> MessageClient | None:
    if company.message_client_type == "digisac":
        digisac_client = (
            db.query(DigisacClientDB).filter_by(company_id=company.id).first()
        )
        if digisac_client:
            return DigisacClient(
                digisac_slug=digisac_client.digisac_slug,
                service_id=digisac_client.service_id,
                default_user_id=digisac_client.digisac_default_user,
                digisac_token=digisac_client.digisac_token,
            )
    else:
        evolutionapi_client = (
            db.query(EvolutionAPIClientDB).filter_by(company_id=company.id).first()
        )
        if evolutionapi_client:
            return EvolutionAPIClient(
                api_key=evolutionapi_client.api_key,
                instance_name=evolutionapi_client.instance_name,
                delay_amount=80000,
            )
    return None


async def get_message(
    request: DigisacRequest | EvolutionAPIRequest,
    message_client: MessageClient,
    assistant: AssistantsClient,
) -> MessageData:
    message_in_text = None
    is_audio = False
    image = None

    if isinstance(request, DigisacRequest):
        match request.data.message.type:
            case "text":
                message_in_text = request.data.message.text
            case "audio" | "ptt":
                is_audio = True
            case "image":
                if isinstance(message_client, DigisacClient):
                    image = message_client.get_file_url(request.data.message.id)
    elif isinstance(request, EvolutionAPIRequest):
        match request.data.messageType:
            case "conversation":
                message_in_text = request.data.message.conversation
            case "extendedTextMessage":
                message_in_text = request.data.message.extendedTextMessage.text
            case "imageMessage":
                message_in_text = request.data.message.imageMessage.caption or ""
                image = request.data.message.base64
            case "audioMessage":
                is_audio = True

    if is_audio:
        file = message_client.get_file_data(request=request)
        if file is not None:
            message_in_text = await assistant.transcribe_audio(file)

    return message_in_text, is_audio, image


async def process_and_send_message(
    text_message: str,
    is_audio: bool,
    media_code: str | None,
    contact: Contact,
    company: Company,
    message_client: MessageClient,
    assistant: AssistantsClient,
    db: Session,
) -> None:
    base64_audio_message = await _generate_audio_message(
        is_audio, text_message, company, assistant, db
    )
    message_type = "audio" if is_audio else "text"
    text_message = None if is_audio else text_message

    await _handle_message_sending_through_client(
        message_client,
        text_message,
        message_type,
        base64_audio_message,
        None,
        contact,
        assistant,
    )
    await _send_medias(media_code, contact, company, message_client, assistant, db)


async def _generate_audio_message(
    is_audio: bool,
    text_message: str,
    company: Company,
    assistant: AssistantsClient,
    db: Session,
) -> str | None:
    base64_audio_message = None

    if is_audio:
        assistant_db = (
            db.query(Assistant)
            .filter_by(assistantId=assistant.openai_assistant_id)
            .first()
        )
        if assistant_db:
            voice = assistant_db.voice
            if voice and company.elevenlabs_api_key:
                elevenlabs_client = ElevenLabsClient(company.elevenlabs_api_key)
                text_message = replace_abbreviations(text_message)
                base64_audio_message = await elevenlabs_client.generate_audio(
                    text_message,
                    voice.elevenlabs_voice_id,
                    voice.stability,
                    voice.similarity_boost,
                    voice.style,
                )

    return base64_audio_message


async def _send_medias(
    media_code: str | None,
    contact: Contact,
    company: Company,
    message_client: MessageClient,
    assistant: AssistantsClient,
    db: Session,
) -> bool:
    if media_code:
        medias = (
            db.query(Media)
            .filter_by(shortcut=media_code, company_id=company.id)
            .order_by(Media.order)
            .all()
        )
        for media in medias:
            content = download_file(media.url)
            if content:
                media_message_data = MediaMessageData(
                    mediatype=media.mediatype,
                    mimetype=media.mimetype,
                    caption=media.nome,
                    media=content,
                    filename=media.nome,
                )

                await _handle_message_sending_through_client(
                    message_client,
                    None,
                    "media",
                    None,
                    media_message_data,
                    contact,
                    assistant,
                )
        return True
    return False


async def _handle_message_sending_through_client(
    message_client: MessageClient,
    text_message: str | None,
    message_type: Literal["text", "audio", "media"],
    base64_audio_message: str | None,
    media_message_data: MediaMessageData | None,
    contact: Contact,
    assistant: AssistantsClient,
) -> None:
    if isinstance(message_client, EvolutionAPIClient):
        message_client.send_message(
            phone_number=contact.phone_number,
            message_type=message_type,
            text_message=text_message,
            audio_message_base64=base64_audio_message,
            media_message=media_message_data,
            assistant_name=assistant.assistant_name,
        )
    elif isinstance(message_client, DigisacClientDB):
        message_client.send_message(
            contact_id=contact.contact_id,
            user_id=None,
            text_message=text_message,
            audio_message_base64=base64_audio_message,
            media_message=media_message_data,
            assistant_name=assistant.assistant_name,
        )
    else:
        raise ValueError(
            "Unsupported message client type"
        )  # TODO: raise custom exception
