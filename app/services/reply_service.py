from datetime import datetime, timedelta
from typing import Literal, Union
import pytz
from sqlalchemy.orm import Session

from app.clients.assistants_client import AssistantsClient
from app.clients.digisac_client import DigisacClient
from app.clients.elevenlabs_client import ElevenLabsClient
from app.clients.evolutionapi_client import EvolutionAPIClient
from app.clients.message_client import MessageClient
from app.db.models import Assistant, Company, Contact, Thread, Voice
from app.exceptions.exceptions import AIResponseException
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.services.crm_service import create_crm_client
from app.utils.create_message_client import create_message_client
from app.utils.api_key_encryption import decrypt_api_key
from app.utils.string_replacements import replace_abbreviations


class ContactService:
    """Encapsulates contact-related operations."""

    def __init__(self, company: Company, db: Session, timezone: str):
        self.company = company
        self.db = db
        self.timezone = pytz.timezone(timezone)

    def get_or_create_contact(
        self,
        contact_id: str,
        message_client: MessageClient,
        payload: Union[DigisacRequest, EvolutionAPIRequest],
    ) -> Contact:
        """Retrieve an existing contact or create one if it doesn't exist."""
        contact = (
            self.db.query(Contact)
            .filter_by(contact_id=contact_id, company_id=self.company.id)
            .first()
        )
        if contact is None:
            contact = self._create_contact(contact_id, message_client, payload)
        else:
            self._update_contact(contact)
        return contact

    def _create_contact(
        self,
        contact_id: str,
        message_client: MessageClient,
        payload: Union[DigisacRequest, EvolutionAPIRequest],
    ) -> Contact:
        """Creates a new contact and persists it in the database."""
        contact_data = message_client.get_contact_data(request=payload)

        # Attempt to create a lead via the CRM client (if available)
        crm_client = create_crm_client(self.company, self.db)
        deal_id = (
            crm_client.create_lead(
                contact_data.contact_name,
                contact_data.contact_name,
                contact_data.phone_number,
            )
            if crm_client and contact_data
            else None
        )

        contact = Contact(
            contact_id=contact_id,
            phone_number=contact_data.phone_number,
            contact_name=contact_data.contact_name,
            last_message_at=datetime.now(self.timezone),
            deal_id=deal_id,
            company_id=self.company.id,
        )
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def _update_contact(self, contact: Contact):
        """Updates an existing contact."""
        now = datetime.now(self.timezone)
        if not contact.receive_ai_replies and contact.last_message_at:
            last_message_tz = contact.last_message_at.replace(tzinfo=self.timezone)
            if now - last_message_tz >= timedelta(days=1):
                self.change_ai_reply_reception(contact, True)

        contact.last_message_at = now
        contact.recall_count = 0
        self.db.commit()

    def change_ai_reply_reception(self, contact: Contact, value: bool):
        """Changes the AI reply reception status for a contact."""
        contact.receive_ai_replies = value
        self.db.commit()

    def reset_contact(self, contact: Contact):
        """Resets contact-related data."""
        contact.current_thread_id = None
        contact.current_assistant = None
        contact.last_message_at = None
        contact.recall_count = 0
        contact.under_appointment_confirmation = False
        contact.awaiting_human_contact = False
        self.db.commit()


class AssistantService:
    """Encapsulates assistant-related operations."""

    def __init__(self, contact: Contact, company: Company, db: Session):
        self.contact = contact
        self.company = company
        self.db = db

    def get_assistant(self) -> AssistantsClient:
        """Retrieve the assistant for the contact."""
        assistant = (
            self.db.query(Assistant)
            .filter_by(id=self.contact.current_assistant, company_id=self.company.id)
            .first()
            if self.contact.current_assistant
            else self.company.default_assistant
        )
        if not self.contact.current_assistant:
            self.contact.current_assistant = assistant.id
            self.db.commit()

        return AssistantsClient(
            assistant_name=assistant.assistant_name,
            openai_assistant_id=assistant.openai_assistant_id,
            openai_api_key=self.company.openai_api_key,
        )

    def execute_thread(self, message: str, image: str) -> str:
        """Runs or creates a thread for the assistant."""
        current_thread_id = (
            self.contact.current_thread.thread_id
            if self.contact.current_thread
            else None
        )

        assistant = self.get_assistant()
        if message:
            assistant.add_message(message=message, thread_id=current_thread_id)
        if image:
            image_id = assistant.upload_image(image)
            assistant.add_message(
                message=None,
                is_image=True,
                image_id=image_id,
                thread_id=current_thread_id,
            )

        result = assistant.create_or_run_thread(thread_id=current_thread_id)

        if not self.contact.current_thread:
            self._assign_thread_to_contact(result.thread_id)

        return result.text_response

    def _assign_thread_to_contact(self, thread_id: str):
        """Assign a new thread to the contact."""
        thread = Thread(
            thread_id=thread_id,
            last_message_from="assistant",
            contact_id=self.contact.id,
        )
        self.db.add(thread)
        self.contact.current_thread = thread
        self.db.commit()


class MessageHandlerService:
    """Encapsulates logic for generating messages (audio/text) and delivering them."""

    def __init__(
        self,
        assistant: AssistantsClient,
        message_client: MessageClient,
        company: Company,
        db: Session,
    ):
        self.assistant = assistant
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
                message = await self.assistant.transcribe_audio(file)

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
            .filter_by(openai_assistant_id=self.assistant.openai_assistant_id)
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
            text=text_message,
            voice_id=voice.elevenlabs_voice_id,
            stability=voice.stability,
            similarity_boost=voice.similarity_boost,
            style=voice.style,
        )

    def _send_message(
        self,
        message_type: Literal["text", "audio"],
        text_message: str | None,
        audio_message_base64: str | None,
        contact: Contact,
    ):
        """Sends a message to the contact based on the client type."""
        if isinstance(self.message_client, EvolutionAPIClient):
            self.message_client.send_message(
                phone_number=contact.phone_number,
                message_type=message_type,
                text_message=text_message,
                audio_message_base64=audio_message_base64,
                media_message=None,
                assistant_name=self.assistant.assistant_name,
            )
        elif isinstance(self.message_client, DigisacClient):
            self.message_client.send_message(
                contact_id=contact.contact_id,
                user_id=None,
                text_message=text_message,
                audio_message_base64=audio_message_base64,
                media_message=None,
                assistant_name=self.assistant.assistant_name,
            )
        else:
            raise ValueError(
                "Unsupported message client type"
            )  # TODO: raise AppException

    async def handle_message_response(
        self,
        is_audio: bool,
        text_message: str,
        contact: Contact,
    ):
        base64_audio_message = await self._generate_audio_message(
            text_message=text_message,
            is_audio=is_audio,
        )
        print(f"Generated base64 audio message: {base64_audio_message}")

        # Determine the message type and send the message
        if is_audio and base64_audio_message:
            message_type = "audio"
            text_message = None
        else:
            message_type = "text"

        self._send_message(
            message_type=message_type,
            text_message=text_message,
            audio_message_base64=base64_audio_message,
            contact=contact,
        )


class ReplyService:
    """Main service for generating replies."""

    def __init__(
        self, db: Session, payload: Union[DigisacRequest, EvolutionAPIRequest]
    ):
        self.db = db
        self.payload = payload

    async def generate_reply(self, company_slug: str, token: str):
        """Main function to generate a reply."""

        company = (
            self.db.query(Company)
            .filter_by(slug=company_slug, token=token, is_active=True)
            .first()
        )
        if not company:
            raise Exception("Company not found or inactive")

        message_client = create_message_client(company, self.db)
        contact_id = (
            self.payload.data.contactId
            if isinstance(self.payload, DigisacRequest)
            else self.payload.data.key.remoteJid
        )

        # Handle contact creation or retrieval
        contact_service = ContactService(company, self.db, company.timezone)
        contact = contact_service.get_or_create_contact(
            contact_id, message_client, self.payload
        )

        if not contact.receive_ai_replies:
            return

        if not await self._handle_request_early_return(contact, company):
            return

        # Initialize the assistant
        assistant_service = AssistantService(contact, company, self.db)
        assistant = assistant_service.get_assistant()

        message_handler_service = MessageHandlerService(
            assistant, message_client, company, self.db
        )

        # Process the message or media content
        message, is_audio, image = (
            await message_handler_service.process_message_content(self.payload)
        )

        if not message and not image:
            return

        # Handle assistant replies
        try:
            response = assistant_service.execute_thread(message, image)
            await message_handler_service.handle_message_response(
                is_audio, response, contact
            )
            return True
        except AIResponseException as e:
            message_handler_service._send_message(
                "text",
                company.ai_reply_error_message
                or "Sorry, an error occurred. Could you repeat your last message?",
                None,
                contact,
            )
            return False

    async def _handle_request_early_return(self, contact: Contact, company: Company):
        contact_service = ContactService(company, self.db, company.timezone)

        if isinstance(self.payload, DigisacRequest):
            if self.payload.data.command == "reset":
                contact_service.reset_contact(contact)
        elif isinstance(self.payload, EvolutionAPIRequest):
            if self.payload.data.key.fromMe:
                contact_service.change_ai_reply_reception(contact, False)
                return False
        return True
