from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.new_models import Assistant, Company, Contact
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client


def reschedule_event_doc():
    return FunctionToolParam(
        function={
            "name": "reschedule_event",
            "description": "Reschedules an event to a new date and time",
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
                    "new_datetime": {
                        "type": "string",
                        "description": "New date and time for the event, in the format DD-MM-YYYYTHH:MM:SS",
                    }
                },
                "additionalProperties": False,
                "required": [
                    "agenda_address",
                    "original_event_title",
                    "original_event_start_datetime",
                    "new_datetime"
                ]
            }
        },
        type="function"
    )


@register_function(reschedule_event_doc())
async def reschedule_event(
        assistant_id: str,
        agenda_address: str,
        original_event_title: str,
        original_event_start_datetime: str,
        new_datetime: str,
        contact: Contact,
) -> bool:
    status = False

    with retornar_sessao() as db:
        assistant = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        if not assistant:
            raise FailedFunctionRunException(detail='Assistant not found in the database', function_name=reschedule_event.__name__)
        
        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(detail='Company not found in the database', function_name=reschedule_event.__name__)

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(detail='Could not create the agenda client', function_name=reschedule_event.__name__)

        status = await agenda_client.reschedule_event(
            agenda_address,
            original_event_start_datetime,
            original_event_title,
            new_datetime
        )

    return status
