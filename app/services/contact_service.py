from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.db.models import Contact
from app.clients.message_client import MessageClient


async def change_awaiting_human_contact(
    contact: Contact, value: bool, db: Session
) -> None:
    contact.awaiting_human_contact = value
    db.commit()


async def end_contact(
    contact: Contact, message_client: MessageClient, db: Session
) -> None:
    if isinstance(message_client, DigisacClient):
        message_client.close_contact_ticket(
            contact.contact_id, ticket_topic_ids=[], comments="", by_user_id=None
        )
    # await reset_contact(contact, db)
