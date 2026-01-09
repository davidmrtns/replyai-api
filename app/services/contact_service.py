from datetime import datetime, timedelta
from typing import Union
import pytz
from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.db.models import Company, Contact, Department
from app.clients.message_client import MessageClient
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.services.crm_service import create_crm_client


class ContactService:
    """Encapsulates contact-related operations."""

    def __init__(self, company: Company, db: Session, timezone: str = "UTC"):
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

    def get_contact_by_phone_number(
        self,
        phone_number: str,
        message_client: MessageClient,
    ) -> Contact:
        """Retrieve a contact by phone number."""
        contact = (
            self.db.query(Contact)
            .filter_by(phone_number=phone_number, company_id=self.company.id)
            .first()
        )
        if not contact:
            contact_name = "Unknown"  # TODO: find a way to get contact name
            contact_id = message_client.get_contact_id(
                phone_number=phone_number,
            )

            contact = Contact(
                contact_id=contact_id,
                phone_number=phone_number,
                contact_name=contact_name,
                last_message_at=datetime.now(self.timezone),
                deal_id=None,
                company_id=self.company.id,
            )
        return contact

    def transfer_contact_to_department(
        self,
        contact: Contact,
        message_client: MessageClient,
        department: Department,
    ) -> None:
        """Transfers a contact to a specified department."""
        if isinstance(message_client, DigisacClient):
            message_client.transfer_contact(
                contact_id=contact.contact_id,
                department_id=department.digisac_department_id,
                user_id=department.digisac_user_id,
                by_user_id=None,
                comments=department.contact_transfer_comment,
            )

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

    def change_awaiting_human_contact(self, contact: Contact, value: bool) -> None:
        """Defines if a contact is awaiting human contact."""
        contact.awaiting_human_contact = value
        self.db.commit()

    def end_contact(self, contact: Contact, message_client: MessageClient) -> None:
        """Ends the contact interaction and resets its data."""
        if isinstance(message_client, DigisacClient):
            message_client.close_contact_ticket(
                contact.contact_id, ticket_topic_ids=[], comments="", by_user_id=None
            )

        self.reset_contact(contact)
