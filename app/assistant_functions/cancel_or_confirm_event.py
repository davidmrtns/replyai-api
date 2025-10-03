from typing import Literal

from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.new_models import Assistant, Company
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client


def cancel_or_confirm_event_doc():
    return FunctionToolParam(
        function={
            "name": "cancel_or_confirm_event",
            "description": "Edits an event, canceling or confirming it",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "agenda_address": {
                        "type": "string",
                        "description": "The agenda email address, as given in the start of the conversation"
                    },
                    "original_event_title": {
                        "type": "string",
                        "description": "The event title, strictly as received in the start of the conversation"
                    },
                    "original_event_start_datetime": {
                        "type": "string",
                        "description": "The event start date and time, in the format DD-MM-YYYYTHH:MM:SS, strictly as received in the start of the conversation"
                    },
                    "action": {
                        "type": "string",
                        "description": "'cancel' to cancel the event, 'confirm' to confirm the event, according to the user's request",
                    }
                },
                "additionalProperties": False,
                "required": [
                    "agenda_address",
                    "original_event_title",
                    "original_event_start_datetime",
                    "action"
                ]
            }
        },
        type="function"
    )


@register_function(cancel_or_confirm_event_doc())
async def cancel_or_confirm_event(
        assistant_id: str,
        agenda_address: str,
        original_event_title: str,
        original_event_start_datetime: str,
        action: Literal['cancel', 'confirm'],
) -> bool:
    status = False

    with retornar_sessao() as db:
        assistant = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        if not assistant:
            raise FailedFunctionRunException(detail='Assistant not found in the database', function_name=cancel_or_confirm_event.__name__)
        
        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(detail='Company not found in the database', function_name=cancel_or_confirm_event.__name__)

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(detail='Could not create the agenda client', function_name=cancel_or_confirm_event.__name__)

        if action == 'cancel':
            status = await agenda_client.cancel_event(
                agenda_address,
                original_event_start_datetime,
                original_event_title,
                company.event_cancellation_type
            )
        elif action == 'confirm':
            status = await agenda_client.confirm_event(
                agenda_address,
                original_event_start_datetime,
                original_event_title
            )
    return status
