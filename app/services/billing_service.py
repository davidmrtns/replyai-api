import json

from sqlalchemy.orm import Session

from app.clients.asaas_client import AsaasClient
from app.db.new_models import Assistant, Company, AsaasClient as AsaasClientDB
from app.services import RespostaFinanceiro
from app.types.types import BillingResponse
from app.clients.assistants_client import AssistantsClient
from app.utils.logger import logger


def create_financial_clients(
        company: Company,
        db: Session,
        client_number: int | None = None
) -> list[AsaasClient] | AsaasClient:
    if company.financial_client_type != 'asaas':
        return []

    query = db.query(AsaasClientDB).filter_by(id_empresa=company.id)

    if client_number is not None:
        query = query.filter_by(client_number=client_number)

    clients = [AsaasClient(token=c.token) for c in query.all()]

    return clients[0] if client_number is not None else clients


async def generate_billing_response(
        action: str,
        contact_name: str,
        phone_number: str,
        current_date: str,
        due_date: str,
        billing_description: str,
        company: Company,
        db: Session
)  -> BillingResponse:
    instruction = {
        "acao": action,
        "dados": {
            "contact_name": contact_name,
            "phone_number": phone_number,
            "due_date": due_date,
            "current_date": current_date,
            "billing_description": billing_description
        }
    }

    assistant_db = db.query(Assistant).filter_by(purpose="cobrar", company_id=company.id).first()

    try:
        if assistant_db is not None:
            assistant = AssistantsClient(assistant_name=assistant_db.nome, openai_assistant_id=assistant_db.assistantId, openai_api_key=company.openai_api_key)
            assistant.add_message(message=json.dumps(instruction))
            response, thread_id = assistant.create_or_run_thread() # TODO: check if i can use the thread service here
            response_to_obj = RespostaFinanceiro.from_dict(json.loads(response))
            return response_to_obj, thread_id
    except Exception as e:
        logger.exception(f"Error generating billing response: {e}")
    return None, None
