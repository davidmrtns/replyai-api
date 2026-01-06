from sqlalchemy.orm import Session

from app.db.database import get_db_session_with_context
from app.db.models import Company
from app.jobs.base import Job
from app.services.billing_service import (
    create_financial_clients,
    process_multiple_payments,
)
from app.services.reply_service import ContactService
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
        contact_service = ContactService(company, db, company.timezone)
        message_client = create_message_client(company, db)
        financial_clients = create_financial_clients(company, db)

        for financial_client in financial_clients:
            response = financial_client.list_payments(
                status="OVERDUE",
                limit="100",
            )

            payload = response.json()
            await process_multiple_payments(
                company,
                financial_client,
                message_client,
                contact_service,
                payload,
                "charge_defaulters",
                db,
                company.send_due_payments_on_charge,
            )
