from openai.types.beta import FunctionToolParam

from app.assistant_functions import _create_agenda_client, _get_variables
from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao


def add_event_to_agenda_doc():
    return FunctionToolParam(
        function={
            "name": "add_event_to_agenda",
            "description": "Adds an event to a given agenda on a given date",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "agenda_code": {
                        "type": "string",
                        "description": "The agenda code, as chosen by the user"
                    },
                    "date": {
                        "type": "string",
                        "description": "The date chosen by the user, in the format DD-MM-YYYYTHH:MM:SS"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the event"
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the event, if applicable"
                    },
                    "localization": {
                        "type": "string",
                        "description": "The localization of the event, if applicable"
                    }
                },
                "additionalProperties": False,
                "required": [
                    "agenda_code",
                    "date",
                    "title",
                    "description",
                    "localization"
                ]
            }
        },
        type="function"
    )


@register_function(add_event_to_agenda_doc())
async def add_event_to_agenda(
        assistant_id: str,
        agenda_code: str,
        date: str,
        title: str,
        description: str,
        localization: str
) -> bool:
    status = False

    with retornar_sessao() as db:
        company, _, agenda_client, agenda = await _get_variables(assistant_id, agenda_code, db)
        
        agenda_client = _create_agenda_client(company, db)
        if agenda_client is None:
            return status
        
        await agenda_client.cadastrar_evento(agenda=agenda.endereco, data=date,
                                                 titulo=title, descricao=description, localizacao=localization)
        status = True # TODO: get the status from the create_event method, when improved
    
    return status
