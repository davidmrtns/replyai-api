from typing import Union
from sqlalchemy.orm import Session

from app.db.models import Company, Contact
from app.exceptions.exceptions import AIResponseException
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.services.contact_service import ContactService
from app.services.message_handler_service import MessageHandlerService
from app.services.thread_service import ThreadService
from app.utils.create_message_client import create_message_client


class ReplyService:
    """Service for generating replies."""

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
        thread_service = ThreadService(contact, company, self.db)
        assistants_client = thread_service.get_assistants_client()

        message_handler_service = MessageHandlerService(
            assistants_client, message_client, company, self.db
        )

        # Process the message or media content
        message, is_audio, image = (
            await message_handler_service.process_message_content(self.payload)
        )

        if not message and not image:
            return

        # Handle assistant replies
        try:
            response = thread_service.execute_thread(message, image)
            await message_handler_service.send_message(
                text_message=response,
                contact=contact,
                message_type="audio" if is_audio else "text",
            )
            return True
        except AIResponseException:
            message_handler_service.send_message(
                text_message=(
                    company.ai_reply_error_message
                    or "Sorry, an error occurred. Could you repeat your last message?"
                ),
                contact=contact,
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
