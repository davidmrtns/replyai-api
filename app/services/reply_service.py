from typing import List, Union
from sqlalchemy.orm import Session

from app.db.models import Company, Contact
from app.exceptions.exceptions import AIResponseException
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.services.contact_service import ContactService
from app.services.message_handler_service import MessageHandlerService
from app.services.thread_service import ThreadService
from app.utils.create_message_client import create_message_client
from app.utils.iterable_utils import has_entry_with_attr


class ReplyService:
    """Service for generating replies."""

    def __init__(
        self, db: Session, payloads: List[Union[DigisacRequest, EvolutionAPIRequest]]
    ):
        self.db = db
        self.payloads = payloads

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
            self.payloads[0].data.contactId
            if isinstance(self.payloads[0], DigisacRequest)
            else self.payloads[0].data.key.remoteJid
        )

        # Handle contact creation or retrieval
        contact_service = ContactService(company, self.db, company.timezone)
        contact = contact_service.get_or_create_contact(
            contact_id, message_client, self.payloads[0]
        )

        if not contact.receive_ai_replies:
            return

        if not self._handle_request_early_return(contact, company):
            return

        # Initialize the assistant
        thread_service = ThreadService(contact, company, self.db)
        assistants_client = thread_service.get_assistants_client()

        message_handler_service = MessageHandlerService(
            assistants_client, message_client, company, self.db
        )

        # Process the message or media content
        messages, is_any_audio = message_handler_service.process_message_content(
            self.payloads
        )  # TODO: check if there's a better way of doing so, to maintain message and image order

        if len(messages) < 1:
            return

        # Handle assistant replies
        try:
            response = await thread_service.execute_thread(messages)
            message_handler_service.send_message(
                text_message=response,
                contact=contact,
                message_type="audio" if is_any_audio else "text",
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

    def _handle_request_early_return(self, contact: Contact, company: Company):
        contact_service = ContactService(company, self.db, company.timezone)

        if isinstance(self.payloads[0], DigisacRequest):
            if has_entry_with_attr(self.payloads, "data.command", "reset"):
                contact_service.reset_contact(contact)
        elif isinstance(self.payloads[0], EvolutionAPIRequest):
            if has_entry_with_attr(self.payloads, "data.key.fromMe", True):
                contact_service.change_ai_reply_reception(contact, False)
                return False
        return True
