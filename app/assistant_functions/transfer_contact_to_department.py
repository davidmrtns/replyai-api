from typing import Annotated

from langchain.tools import InjectedToolArg, ToolRuntime, tool

from app.assistant_functions.assistant_function import register_tool
from app.clients.digisac_client import DigisacClient
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Company, Department, Thread
from app.exceptions.exceptions import FailedFunctionRunException
from app.services.contact_service import ContactService
from app.utils.create_message_client import create_message_client
from app.utils.model_utils import get_resource_from_db
from app.assistant_functions.runtime_context import RuntimeContext


@register_tool
@tool("transfer_contact_to_department")
def transfer_contact_to_department(
    department_code: str,
    runtime: Annotated[ToolRuntime[RuntimeContext], InjectedToolArg],
) -> bool:
    """Transfer the customer to a specified department."""
    assistant_id = runtime.context["assistant_id"]
    thread_id = runtime.context["thread_id"]
    status = False

    with get_db_session_with_context() as db:
        assistant = get_resource_from_db(Assistant, assistant_id, db)
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
            db.query(Department)
            .filter_by(code=department_code, company_id=company.id)
            .first()
        )
        if not department:
            raise FailedFunctionRunException(
                detail="Department not found in the database",
                function_name=transfer_contact_to_department.__name__,
            )

        contact_service = ContactService(company, db, company.timezone)

        contact_service.change_awaiting_human_contact(contact, True)
        contact_service.transfer_contact_to_department(
            contact, message_client, department
        )

        status = True
    return status
