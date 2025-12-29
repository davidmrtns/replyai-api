import multiprocessing

from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.jobs.jobs import (
    rodar_confirmar_agendamento,
    rodar_avisar_vencimento,
    rodar_cobrar_inadimplentes,
    rodar_retomar_conversa,
)
from app.jobs.sub_jobs import processar_cobranca, processar_nf
from app.routers.routers_helpers import validate_secret_key
from app.schemas.integrations.asaas_schema import (
    AsaasPaymentRequest,
    AsaasInvoiceRequest,
)
from app.schemas.job_schema import JobExecutedResponse, create_job_executed_response
from app.services.billing_service import create_financial_clients
from app.services.company_service import get_company_data


router = APIRouter(dependencies=[Depends(validate_secret_key)])


@router.post("/recall_conversations", response_model=JobExecutedResponse)
async def execute_conversation_recall():
    process = multiprocessing.Process(target=rodar_retomar_conversa)
    process.start()

    return create_job_executed_response(job_name="recall_conversations")


@router.post("/confirm_appointments", response_model=JobExecutedResponse)
async def execute_confirm_appointment():
    process = multiprocessing.Process(target=rodar_confirmar_agendamento)
    process.start()

    return create_job_executed_response(job_name="confirm_appointments")


@router.post("/notify_due_dates", response_model=JobExecutedResponse)
async def execute_notify_due_date():
    process = multiprocessing.Process(target=rodar_avisar_vencimento)
    process.start()

    return create_job_executed_response(job_name="notify_due_dates")


@router.post("/charge_defaulters", response_model=JobExecutedResponse)
async def execute_charge_defaulters():
    process = multiprocessing.Process(target=rodar_cobrar_inadimplentes)
    process.start()

    return create_job_executed_response(job_name="charge_defaulters")


@router.post(
    "/thank_payment/asaas/{slug}/{token}/{client_number}",
    response_model=JobExecutedResponse,
)
async def execute_thank_payment(
    request: AsaasPaymentRequest,
    slug: str,
    token: str,
    client_number: int,
    db: Session = Depends(get_db_session),
):
    company_data = await get_company_data(slug, token, db)
    if company_data is not None:
        company, message_client = company_data
        financial_client = create_financial_clients(company, db, client_number)
        await processar_cobranca(
            "extract_payment_data",
            request.payment.model_dump(),
            "",
            False,
            company,
            message_client,
            financial_client,
            db,
        )
        return create_job_executed_response(job_name="thank_payment")


@router.post(
    "/send_invoice/asaas/{slug}/{token}/{client_number}",
    response_model=JobExecutedResponse,
)
async def execute_send_invoice(
    request: AsaasInvoiceRequest,
    slug: str,
    token: str,
    client_number: int,
    db: Session = Depends(get_db_session),
):
    company_data = await get_company_data(slug, token, db)
    if company_data is not None:
        company, message_client = company_data
        financial_client = create_financial_clients(company, db, client_number)
        await processar_nf(
            "extract_invoice_data",
            request.invoice.model_dump(),
            "",
            company,
            message_client,
            financial_client,
            db,
        )
        return create_job_executed_response(job_name="send_invoice")
