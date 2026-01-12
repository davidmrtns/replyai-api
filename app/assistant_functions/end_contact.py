from openai.types.responses import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.clients.digisac_client import DigisacClient
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Company, Thread
from app.exceptions.exceptions import FailedFunctionRunException
from app.services.contact_service import ContactService
from app.utils.create_message_client import create_message_client
from app.utils.model_utils import get_resource_from_db


def end_contact_doc():
    return FunctionToolParam(
        name="end_contact_doc",
        description="Ends the contact when the issue has been resolved",
        strict=False,
        parameters={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "required": [],
        },
        type="function",
    )


@register_function(end_contact_doc())
async def end_contact_doc(assistant_id: str, thread_id: str, **kwargs) -> bool:
    status = False

    with get_db_session_with_context() as db:
        assistant = await get_resource_from_db(Assistant, assistant_id, db)
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=end_contact_doc.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=end_contact_doc.__name__,
            )

        message_client = create_message_client(company, db)
        if not message_client or not isinstance(message_client, DigisacClient):
            raise FailedFunctionRunException(
                detail="Message client not found or not supported for transfer",
                function_name=end_contact_doc.__name__,
            )

        current_thread = db.query(Thread).filter_by(thread_id=thread_id).first()
        if not current_thread:
            raise FailedFunctionRunException(
                detail="Thread not found in the database",
                function_name=end_contact_doc.__name__,
            )

        contact = current_thread.contact
        if not contact:
            raise FailedFunctionRunException(
                detail="Contact not found in the database",
                function_name=end_contact_doc.__name__,
            )

        contact_service = ContactService(company, db, company.timezone)
        contact_service.end_contact(contact, message_client)

        status = True
    return status
