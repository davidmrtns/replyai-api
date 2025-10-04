from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.clients.digisac_client import DigisacClient
from app.db.database import retornar_sessao
from app.db.new_models import Assistant, Company, Thread
from app.exceptions.exceptions import FailedFunctionRunException
from app.services.contact_service import end_contact
from app.services.message_service import create_message_client


def end_contact_doc():
    return FunctionToolParam(
        function={
            "name": "end_contact_doc",
            "description": "Ends the contact when the issue has been resolved",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
                "required": []
            }
        },
        type="function"
    )


@register_function(end_contact_doc())
async def end_contact_doc(
        assistant_id: str,
        thread_id: str,
        **kwargs
) -> bool:
    status = False

    with retornar_sessao() as db:
        assistant = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        if not assistant:
            raise FailedFunctionRunException(detail='Assistant not found in the database', function_name=end_contact_doc.__name__)
        
        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(detail='Company not found in the database', function_name=end_contact_doc.__name__)

        message_client = create_message_client(company, db)
        if not message_client or not isinstance(message_client, DigisacClient):
            raise FailedFunctionRunException(detail='Message client not found or not supported for transfer', function_name=end_contact_doc.__name__)

        current_thread = db.query(Thread).filter_by(thread_id=thread_id).first()
        if not current_thread:
            raise FailedFunctionRunException(detail='Thread not found in the database', function_name=end_contact_doc.__name__)

        contact = current_thread.contact
        if not contact:
            raise FailedFunctionRunException(detail='Contact not found in the database', function_name=end_contact_doc.__name__)

        await end_contact(contact, message_client, db) # TODO: check if after ending the contact in Digisac clients the sent message will reopen the ticket
        status = True
    return status
