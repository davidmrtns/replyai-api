from sqlalchemy.orm import Session

from app.clients.asaas_client import AsaasClient
from app.clients.message_client import MessageClient
from app.db.database import get_db_session_with_context
from app.db.models import Company
from app.jobs.base import Job
from app.prompts import load_prompt
from app.services.billing_service import create_financial_clients
from app.services.reply_service import (
    AssistantService,
    ContactService,
    MessageHandlerService,
)
from app.utils.create_message_client import create_message_client
from app.utils.logger import log_job_error


class ChargeDefaultersJob(Job):
    name = "charge_defaulters"

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
        message_client = create_message_client(company, db)
        financial_clients = create_financial_clients(company, db)

        for financial_client in financial_clients:
            await self._send_notifications(
                company, financial_client, message_client, db
            )

    async def _send_notifications(
        self,
        company: Company,
        financial_client: AsaasClient,
        message_client,
        db: Session,
    ):
        response = financial_client.list_payments(
            status="OVERDUE",
            limit="100",
        )

        payload = response.json()
        if payload.get("totalCount", 0) > 0:
            for payment in payload.get("data", []):
                await self._process_payment(
                    company, financial_client, message_client, payment, db
                )

    # TODO: unify with function from notify_due_dates.py
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
                "charge_defaulters",
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
