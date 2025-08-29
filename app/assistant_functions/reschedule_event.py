from openai.types.beta import FunctionToolParam

from app.assistant_functions import _get_variables
from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.new_models import Contact
from app.utils.agenda_client import EventoTituloAgenda


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
        _, __, agenda_client, ___ = await _get_variables(assistant_id, None, db)
        
        original_event_data = EventoTituloAgenda(
            title=original_event_title,
            start_datetime=original_event_start_datetime,
            agenda_address=agenda_address
        )

        original_event_data.start_datetime = new_datetime
        await agenda_client.reagendar_evento(original_event_data) # TODO: update this method to accept new datetime
        status = True # TODO: get the status from the reschedule_event method, when improved
    
    return status
