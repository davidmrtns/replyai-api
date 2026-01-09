from typing import Literal
from sqlalchemy.orm import Session

from app.clients.assistants_client import AssistantsClient
from app.clients.digisac_client import DigisacClient
from app.clients.elevenlabs_client import ElevenLabsClient
from app.clients.evolutionapi_client import EvolutionAPIClient
from app.clients.message_client import MediaMessageData, MessageClient
from app.db.models import Assistant, Company, Contact, Voice
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.utils.api_key_encryption import decrypt_api_key
from app.utils.string_replacements import replace_abbreviations


class MessageHandlerService:
    """Encapsulates logic for generating messages (audio/text) and delivering them."""

    def __init__(
        self,
        assistants_client: AssistantsClient,
        message_client: MessageClient,
        company: Company,
        db: Session,
    ):
        self.assistants_client = assistants_client
        self.message_client = message_client
        self.company = company
        self.db = db

    async def process_message_content(
        self, payload: DigisacRequest | EvolutionAPIRequest
    ):
        """Extract the message and media content from the payload."""
        message, is_audio, image = self.message_client.get_message_content(
            request=payload
        )

        # Handle audio transcription if the message is audio
        if is_audio:
            file = self.message_client.get_file_data(request=payload)
            if file:
                message = await self.assistants_client.transcribe_audio(file)

        return message, is_audio, image

    async def _generate_audio_message(
        self,
        text_message: str,
        is_audio: bool,
    ) -> str | None:
        """Generates an audio message using ElevenLabs if `is_audio` is True."""
        if not is_audio:
            return None

        # Fetch the assistant's voice configuration
        assistant_db = (
            self.db.query(Assistant)
            .filter_by(openai_assistant_id=self.assistants_client.openai_assistant_id)
            .first()
        )

        if not assistant_db:
            return None  # No assistant voice configuration available

        voice: Voice = assistant_db.voice
        if not (voice or self.company.elevenlabs_api_key):
            return None  # Missing voice configuration or API key

        # Initialize ElevenLabs client and generate audio
        elevenlabs_client = ElevenLabsClient(
            decrypt_api_key(self.company.elevenlabs_api_key)
        )
        text_message = replace_abbreviations(text_message)
        return await elevenlabs_client.generate_audio(
            text_message=text_message,
            voice_id=voice.elevenlabs_voice_id,
            stability=voice.stability,
            similarity_boost=voice.similarity_boost,
            style=voice.style,
        )

    async def send_message(
        self,
        text_message: str | None,
        contact: Contact,
        message_type: Literal["text", "audio", "media"] = "text",
        media_message: MediaMessageData | None = None,
    ):
        """
        Sends a message to the contact based on the client type.

        Args:
            text_message (str | None): The text content of the message. Should be None if sending audio or media.
            contact (Contact): The contact to whom the message will be sent.
            message_type (Literal["text", "audio", "media"]): The type of message to be sent.
            media_message (MediaMessageData | None): The media content, if sending a media message.
        """
        is_audio = message_type == "audio"

        audio_message_base64 = await self._generate_audio_message(
            text_message=text_message,
            is_audio=is_audio,
        )

        # Clears text message if audio or media
        if (is_audio and audio_message_base64) or message_type == "media":
            text_message = None

        if isinstance(self.message_client, EvolutionAPIClient):
            self.message_client.send_message(
                phone_number=contact.phone_number,
                message_type=message_type,
                text_message=text_message,
                audio_message_base64=audio_message_base64,
                media_message=media_message,
                assistant_name=self.assistants_client.assistant_name,
            )
        elif isinstance(self.message_client, DigisacClient):
            self.message_client.send_message(
                contact_id=contact.contact_id,
                user_id=None,
                text_message=text_message,
                audio_message_base64=audio_message_base64,
                media_message=media_message,
                assistant_name=self.assistants_client.assistant_name,
            )
        else:
            raise ValueError(
                "Unsupported message client type"
            )  # TODO: raise AppException
