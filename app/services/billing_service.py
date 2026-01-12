from typing import Literal

from sqlalchemy.orm import Session

from app.clients.asaas_client import AsaasClient
from app.clients.digisac_client import DigisacClient
from app.clients.message_client import MediaMessageData, MessageClient
from app.db.models import Company, Contact
from app.prompts.load_prompt import load_prompt
from app.services.contact_service import ContactService
from app.services.message_handler_service import MessageHandlerService
from app.services.thread_service import ThreadService
from app.utils import download_file


# TODO: maybe type payments_payload better
async def process_multiple_payments(
    company: Company,
    financial_client: AsaasClient,
    message_client: MessageClient,
    contact_service: ContactService,
    payments_payload: dict,
    prompt_name: str,
    db: Session,
    send_bank_slip: bool = False,
):
    if payments_payload.get("totalCount", 0) > 0:
        for payment in payments_payload.get("data", []):
            await process_payment(
                payment,
                company,
                financial_client,
                message_client,
                contact_service,
                prompt_name,
                db,
                "bank_slip" if send_bank_slip else None,
            )


async def process_payment(
    payment: dict,
    company: Company,
    financial_client: AsaasClient,
    message_client: MessageClient,
    contact_service: ContactService,
    prompt_name: str,
    db: Session,
    send_file: Literal["bank_slip", "invoice"] | None = None,
):
    customer = financial_client.get_customer(payment.get("customer", ""))
    if customer:
        customer = customer.json()

        phone_number = customer.get("mobilePhone", "")
        name = customer.get("name", "")
        due_date = payment.get("dueDate", "")
        payment_description = payment.get("description", "")

        contact = contact_service.get_contact_by_phone_number(
            phone_number, message_client
        )

        prompt = load_prompt(
            prompt_name,
            {
                "name": name,
                "due_date": due_date,
                "description": payment_description,
                "company_name": company.company_name,
            },
        )

        thread_service = ThreadService(contact, company, db)
        response = await thread_service.execute_thread(prompt, None)
        assistants_client = thread_service.get_assistants_client()

        message_handler_service = MessageHandlerService(
            assistants_client, message_client, company, db
        )
        message_handler_service.send_message(text_message=response, contact=contact)

        if send_file:
            if send_file == "bank_slip":
                file_url = payment.get("bankSlipUrl", "")
            else:
                file_url = payment.get("pdfUrl", "")

            send_financial_document_to_contact(
                message_handler_service, file_url, message_client, contact
            )


def send_financial_document_to_contact(
    message_handler_service: MessageHandlerService,
    file_url: str,
    message_client: MessageClient,
    contact: Contact,
):
    file = download_file(file_url)
    if file:
        mediatype = (
            "application/pdf"
            if isinstance(message_client, DigisacClient)
            else "document"
        )

        media_message_data = MediaMessageData(
            mediatype=mediatype,
            mimetype=mediatype,
            caption="",
            media=file,
            filename="file.pdf",
        )

        message_handler_service.send_message(
            text_message=None,
            contact=contact,
            message_type="media",
            media_message=media_message_data,
        )
