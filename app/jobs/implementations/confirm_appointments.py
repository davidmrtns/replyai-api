from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import pytz

from app.clients.agenda_client import ScheduleItem
from app.clients.digisac_client import DigisacClient
from app.clients.message_client import MessageClient
from app.db.database import get_db_session_with_context
from app.db.models import Agenda, Company, Department
from app.jobs.base import Job
from app.services.contact_service import ContactService
from app.services.message_handler_service import MessageHandlerService
from app.services.thread_service import ThreadService
from app.utils.create_message_client import create_message_client
from app.utils.create_agenda_client import create_agenda_client
from app.utils.extract_phone_number import extract_phone_number
from app.prompts.load_prompt import load_prompt
from app.utils.model_utils import apply_model_update
from app.utils.logger import log_job_error


class ConfirmAppointmentsJob(Job):
    name = "confirm_appointments"

    async def run(self) -> None:
        with get_db_session_with_context() as db:
            companies = (
                db.query(Company)
                .filter_by(appointment_confirmation_is_active=True, is_active=True)
                .all()
            )

            for company in companies:
                try:
                    await self._process_company(company, db)
                except Exception as e:
                    log_job_error(self.name, company.slug, e)

    async def _process_company(self, company: Company, db: Session):
        contact_service = ContactService(company, db, company.timezone)

        timezone = company.timezone or "UTC"
        tz = pytz.timezone(timezone)
        today = datetime.now(tz)
        today_formatted = today.strftime("%Y-%m-%dT%H:%M:%S")
        next_day = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        message_client = create_message_client(company, db)
        agenda_client = create_agenda_client(company, db)
        agendas = db.query(Agenda).filter_by(company_id=company.id).all()

        responses = await agenda_client.get_schedules(
            agendas=[agenda.address for agenda in agendas], date=next_day
        )

        for response in responses:
            for event in response.schedule_items:
                await self._process_event(
                    event, contact_service, message_client, company, db, today_formatted
                )

    async def _process_event(
        self,
        event: ScheduleItem,
        contact_service: ContactService,
        message_client: MessageClient,
        company: Company,
        db: Session,
        today_formatted: str,
    ):
        subject = event.subject

        phone_number = extract_phone_number(subject)
        contact = contact_service.get_contact_by_phone_number(
            phone_number, message_client
        )

        if not contact.under_appointment_confirmation:
            apply_model_update(contact, {"under_appointment_confirmation": True})
            db.commit()

            prompt = load_prompt(
                "confirm_appointment",
                {
                    "today": today_formatted,
                    "event_subject": subject,
                    "event_date": event.start.date_time,
                    "event_location": event.location,
                    "company_name": company.company_name,
                },
            )

            thread_service = ThreadService(contact, company, db)
            response = thread_service.execute_thread(prompt, None)
            assistants_client = thread_service.get_assistants_client()

            message_handler_service = MessageHandlerService(
                assistants_client, message_client, company, db
            )
            await message_handler_service.send_message(
                text_message=response, contact=contact
            )

            if isinstance(message_client, DigisacClient):
                department = (
                    db.query(Department)
                    .filter_by(
                        is_confirmation_department=True,
                        digisac_client_id=message_client.message_client_id,
                    )
                    .first()
                )
                if department:
                    contact_service.transfer_contact_to_department(
                        contact, message_client, department
                    )
