from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.clients.message_client import MessageClient
from app.db.database import get_db_session_with_context
from app.db.models import Company, Contact
from app.jobs.base import Job
from app.prompts.load_prompt import load_prompt
from app.services.message_handler_service import MessageHandlerService
from app.services.thread_service import ThreadService
from app.services.contact_service import ContactService
from app.utils.create_message_client import create_message_client
from app.utils.logger import log_job_error
from app.utils.model_utils import apply_model_update


class RecallConversationsJob(Job):
    name = "recall_conversations"

    async def run(self) -> None:
        with get_db_session_with_context() as db:
            companies = (
                db.query(Company).filter_by(recall_is_active=True, is_active=True).all()
            )

            for company in companies:
                try:
                    await self._process_company(company, db)
                except Exception as e:
                    log_job_error(self.name, company.slug, e)

    async def _process_company(self, company: Company, db: Session):
        message_client = create_message_client(company, db)
        contact_service = ContactService(company, db, company.timezone)

        today = datetime.now()

        std_recall_timeout = company.recall_timeout_minutes or 60
        std_recall_timeout_timedelta = today - timedelta(minutes=std_recall_timeout)

        final_recall_timeout = company.final_recall_timeout_minutes or 1440
        final_recall_timeout_timedelta = today - timedelta(minutes=final_recall_timeout)

        contacts = (
            db.query(Contact)
            .filter(
                Contact.company_id == company.id,
                or_(
                    and_(
                        Contact.last_message_at <= std_recall_timeout_timedelta,
                        Contact.recall_count < company.recall_quantity - 1,
                        Contact.receive_ai_replies == True,
                        Contact.awaiting_human_contact == False,
                    ),
                    and_(
                        Contact.last_message_at <= final_recall_timeout_timedelta,
                        Contact.recall_count == company.recall_quantity - 1,
                        Contact.receive_ai_replies == True,
                        Contact.awaiting_human_contact == False,
                    ),
                ),
            )
            .all()
        )

        for contact in contacts:
            await self._process_contact(
                contact, company, message_client, contact_service, db
            )

    async def _process_contact(
        self,
        contact: Contact,
        company: Company,
        message_client: MessageClient,
        contact_service: ContactService,
        db: Session,
    ):
        if contact.recall_count < company.recall_quantity - 1:
            prompt_name = "recall_conversation"
        else:
            prompt_name = "end_conversation"

        prompt = load_prompt(prompt_name, {"company_name": company.company_name})

        if isinstance(message_client, DigisacClient):
            should_break = await self._process_digisac_contact(
                contact, message_client, contact_service, db
            )
            if should_break:
                return

        thread_service = ThreadService(contact, company, db)
        response = await thread_service.execute_thread(prompt, None)
        assistants_client = thread_service.get_assistants_client()

        message_handler_service = MessageHandlerService(
            assistants_client, message_client, company, db
        )
        await message_handler_service.send_message(
            text_message=response, contact=contact
        )

        apply_model_update(contact, {"recall_count": contact.recall_count + 1})
        db.commit()

    async def _process_digisac_contact(
        self,
        contact: Contact,
        message_client: DigisacClient,
        contact_service: ContactService,
        db: Session,
    ) -> bool:
        ticket_id, last_message_id = message_client.get_ticket_and_last_message_ids(
            contact.contact_id
        )
        if ticket_id is None:
            await contact_service.reset_contact(contact)
            return True
        else:
            if last_message_id is None:
                return True
            message_origin = message_client.get_message_origin(last_message_id)
            if message_origin is None or message_origin == "user":
                await contact_service.reset_contact(contact, db)
                return True
        return False
