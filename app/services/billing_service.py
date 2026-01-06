import json
from typing import List

from sqlalchemy.orm import Session

from app.clients.asaas_client import AsaasClient
from app.clients.digisac_client import DigisacClient
from app.clients.message_client import MediaMessageData, MessageClient
from app.db.models import Assistant, Company, AsaasClient as AsaasClientDB, Contact
from app.prompts.load_prompt import load_prompt
from app.services import RespostaFinanceiro
from app.clients.assistants_client import AssistantsClient
from app.services.reply_service import (
    AssistantService,
    ContactService,
    MessageHandlerService,
)
from app.utils import download_file
from app.utils.logger import logger


# TODO: move to utils file
def create_financial_clients(
    company: Company, db: Session, client_number: int | None = None
) -> List[AsaasClient]:
    if company.financial_client_type != "asaas":
        return []

    query = db.query(AsaasClientDB).filter_by(id_empresa=company.id)

    if client_number is not None:
        query = query.filter_by(client_number=client_number)

    clients = [AsaasClient(token=c.token) for c in query.all()]

    return clients


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
                send_bank_slip,
            )


async def process_payment(
    payment: dict,
    company: Company,
    financial_client: AsaasClient,
    message_client: MessageClient,
    contact_service: ContactService,
    prompt_name: str,
    db: Session,
    send_bank_slip: bool = False,
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
            },
        )

        assistant_service = AssistantService(contact, company, db)
        response = assistant_service.execute_thread(prompt, None)
        assistant = assistant_service.get_assistant()

        message_handler_service = MessageHandlerService(
            assistant, message_client, company, db
        )
        await message_handler_service.handle_message_response(False, response, contact)

        if send_bank_slip:
            await send_bank_slip_to_contact(
                message_handler_service, payment, message_client, contact
            )


async def send_bank_slip_to_contact(
    message_handler_service: MessageHandlerService,
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

            message_handler_service.send_message(
                message_type="media",
                text_message=None,
                audio_message_base64=None,
                media_message=media_message_data,
                contact=contact,
            )


# TODO: check if can be removed
async def generate_billing_response(
    action: str,
    contact_name: str,
    phone_number: str,
    current_date: str,
    due_date: str,
    billing_description: str,
    company: Company,
    db: Session,
):
    instruction = {
        "acao": action,
        "dados": {
            "contact_name": contact_name,
            "phone_number": phone_number,
            "due_date": due_date,
            "current_date": current_date,
            "billing_description": billing_description,
        },
    }

    assistant_db = (
        db.query(Assistant).filter_by(purpose="cobrar", company_id=company.id).first()
    )

    try:
        if assistant_db is not None:
            assistant = AssistantsClient(
                assistant_name=assistant_db.nome,
                openai_assistant_id=assistant_db.assistantId,
                openai_api_key=company.openai_api_key,
            )
            assistant.add_message(message=json.dumps(instruction))
            response, thread_id = (
                assistant.create_or_run_thread()
            )  # TODO: check if i can use the thread service here
            response_to_obj = RespostaFinanceiro.from_dict(json.loads(response))
            return response_to_obj, thread_id
    except Exception as e:
        logger.exception(f"Error generating billing response: {e}")
    return None, None
