from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.routers.routers_helpers import validate_secret_key
from app.schemas.integrations.asaas_schema import (
    AsaasInvoiceRequest,
    AsaasPaymentRequest,
)
from app.services.billing_service import process_payment
from app.services.company_service import get_company_by_slug_and_token
from app.services.reply_service import ContactService
from app.utils.create_financial_clients import create_financial_clients
from app.utils.create_message_client import create_message_client


router = APIRouter(dependencies=[Depends(validate_secret_key)])


@router.post("/thank_payment/asaas/{company_slug}/{token}/{client_number}")
async def execute_thank_payment(
    company_slug: str,
    token: str,
    client_number: int,
    request: AsaasPaymentRequest,
    db: Session = Depends(get_db_session),
):
    company = get_company_by_slug_and_token(company_slug, token, db)
    message_client = create_message_client(company, db)
    financial_client = create_financial_clients(company, db, client_number)
    contact_service = ContactService(company, db, company.timezone)

    await process_payment(
        request.payment.model_dump(),
        company,
        financial_client,
        message_client,
        contact_service,
        "thank_payment",
        db,
    )
    return True


@router.post("/send_invoice/asaas/{company_slug}/{token}/{client_number}")
async def execute_send_invoice(
    company_slug: str,
    token: str,
    client_number: int,
    request: AsaasInvoiceRequest,
    db: Session = Depends(get_db_session),
):
    company = get_company_by_slug_and_token(company_slug, token, db)
    message_client = create_message_client(company, db)
    financial_client = create_financial_clients(company, db, client_number)
    contact_service = ContactService(company, db, company.timezone)

    await process_payment(
        request.invoice.model_dump(),
        company,
        financial_client,
        message_client,
        contact_service,
        "send_invoice",
        db,
        "invoice",
    )
    return True
