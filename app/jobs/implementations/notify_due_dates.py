from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import Session

from app.clients.asaas_client import AsaasClient
from app.clients.digisac_client import DigisacClient
from app.clients.message_client import MediaMessageData, MessageClient
from app.db.database import get_db_session_with_context
from app.db.models import Company, Contact
from app.jobs.base import Job
from app.prompts.load_prompt import load_prompt
from app.services.billing_service import create_financial_clients
from app.services.reply_service import (
    AssistantService,
    ContactService,
    MessageHandlerService,
)
from app.utils.create_message_client import create_message_client
from app.utils.download_file import download_file
from app.utils.logger import log_job_error


class NotifyDueDates(Job):
    name = "notify_due_dates"

    async def run(self) -> None:
        async with get_db_session_with_context() as db:
            companies = (
                db.query(Company)
                .filter_by(charge_due_payments_is_active=True, is_active=True)
                .all()
            )

            for company in companies:
                try:
                    await self._process_company(company, db)
                    pass
                except Exception as e:
                    log_job_error(self.name, company.slug, e)

    async def _process_company(self, company: Company, db: Session):
        timezone = company.timezone or "UTC"
        tz = pytz.timezone(timezone)

        today = datetime.now(tz)
        today_formatted = today.strftime("%Y-%m-%d")
        next_day = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        three_days_ahead = (today + timedelta(days=3)).strftime("%Y-%m-%d")

        message_client = create_message_client(company, db)
        financial_clients = create_financial_clients(company, db)

        for financial_client in financial_clients:
            await self._send_notifications(
                company, financial_client, message_client, next_day, db
            )
            await self._send_notifications(
                company, financial_client, message_client, three_days_ahead, db
            )

    async def _send_notifications(
        self,
        company: Company,
        financial_client: AsaasClient,
        message_client: MessageClient,
        due_date: str,
        db: Session,
    ):
        response = financial_client.list_payments(
            due_date_le=due_date,
            due_date_ge=due_date,
            status="PENDING",
            limit="100",
        )

        payload = response.json()
        if payload.get("totalCount", 0) > 0:
            for payment in payload.get("data", []):
                await self._process_payment(
                    company, financial_client, message_client, payment, db
                )

    async def _process_payment(
        self,
        company: Company,
        financial_client: AsaasClient,
        message_client: MessageClient,
        payment: dict,
        db: Session,
    ):
        customer = financial_client.get_customer(payment.get("customer", ""))
        if customer:
            phone_number = customer.get("mobilePhone", "")
            name = customer.get("name", "")
            due_date = payment.get("dueDate", "")
            payment_description = payment.get("description", "")

            contact_service = ContactService(company, db, company.timezone)
            contact = contact_service.get_contact_by_phone_number(
                phone_number, message_client
            )

            prompt = load_prompt(
                "notify_due_dates",
                {
                    "name": name,
                    "due_date": due_date,
                    "description": payment_description,
                },
            )

            assistant_service = AssistantService(contact, company, db)
            response = assistant_service.execute_thread(prompt, None)
            assistant = assistant_service.get_assistant()

            message_handler_service = MessageHandlerService(
                assistant, message_client, company, db
            )
            await message_handler_service.handle_message_response(
                False, response, contact
            )

            if company.send_due_payments_on_charge:
                await self._send_bank_slip(
                    message_handler_service, payment, message_client, contact
                )

    async def _send_bank_slip(
        self,
        message_service: MessageHandlerService,
        payment: dict,
        message_client: MessageClient,
        contact: Contact,
    ):
        bank_slip_url = payment.get("bankSlipUrl", "")
        if bank_slip_url:
            bank_slip = download_file(bank_slip_url)
            if bank_slip:
                mediatype = (
                    "application/pdf"
                    if isinstance(message_client, DigisacClient)
                    else "document"
                )

                media_message_data = MediaMessageData(
                    mediatype=mediatype,
                    mimetype=mediatype,
                    caption="",
                    media=bank_slip,
                    filename="file.pdf",
                )

                message_service.send_message(
                    message_type="media",
                    text_message=None,
                    audio_message_base64=None,
                    media_message=media_message_data,
                    contact=contact,
                )
