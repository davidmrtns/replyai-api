from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.clients.digisac_client import DigisacClient
from app.db.database import retornar_sessao
from app.db.models import Departamento
from app.db.new_models import Assistant, Company, Thread
from app.exceptions.exceptions import FailedFunctionRunException
from app.services.contact_service import change_awaiting_human_contact, transfer_contact
from app.services.message_service import create_message_client


def transfer_contact_to_department_doc():
    return FunctionToolParam(
        function={
            "name": "transfer_contact_to_department",
            "description": "Transfers the customer to a specified department",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "department_code": {
                        "type": "string",
                        "description": "The department code, as chosen by the user",
                    }
                },
                "additionalProperties": False,
                "required": ["department_code"],
            },
        },
        type="function",
    )


@register_function(transfer_contact_to_department_doc())
async def transfer_contact_to_department(
    assistant_id: str, thread_id: str, department_code: str
) -> bool:
    status = False

    with retornar_sessao() as db:
        assistant = (
            db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        )
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=transfer_contact_to_department.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=transfer_contact_to_department.__name__,
            )

        message_client = create_message_client(company, db)
        if not message_client or not isinstance(message_client, DigisacClient):
            raise FailedFunctionRunException(
                detail="Message client not found or not supported for transfer",
                function_name=transfer_contact_to_department.__name__,
            )

        current_thread = db.query(Thread).filter_by(thread_id=thread_id).first()
        if not current_thread:
            raise FailedFunctionRunException(
                detail="Thread not found in the database",
                function_name=transfer_contact_to_department.__name__,
            )

        contact = current_thread.contact
        if not contact:
            raise FailedFunctionRunException(
                detail="Contact not found in the database",
                function_name=transfer_contact_to_department.__name__,
            )

        department = (
            db.query(Departamento)
            .filter_by(codigo=department_code, id_empresa=company.id)
            .first()
        )
        if not department:
            raise FailedFunctionRunException(
                detail="Department not found in the database",
                function_name=transfer_contact_to_department.__name__,
            )

        await change_awaiting_human_contact(contact, True, db)
        await transfer_contact(message_client, contact, department)
        status = True
    return status
