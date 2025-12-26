from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.new_models import Assistant, Company, Agenda
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client


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
                        "description": "The agenda code, as chosen by the user",
                    },
                    "date": {
                        "type": "string",
                        "description": "The date chosen by the user, in the format DD-MM-YYYYTHH:MM:SS",
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the event",
                    },
                    "description": {
                        "type": "string",
                        "description": "The description of the event, if applicable",
                    },
                    "localization": {
                        "type": "string",
                        "description": "The localization of the event, if applicable",
                    },
                },
                "additionalProperties": False,
                "required": [
                    "agenda_code",
                    "date",
                    "title",
                    "description",
                    "localization",
                ],
            },
        },
        type="function",
    )


@register_function(add_event_to_agenda_doc())
async def add_event_to_agenda(
    assistant_id: str,
    thread_id: str,
    agenda_code: str,
    date: str,
    title: str,
    description: str,
    localization: str,
) -> bool:
    status = False

    with retornar_sessao() as db:
        assistant = (
            db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        )
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=add_event_to_agenda.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=add_event_to_agenda.__name__,
            )

        agenda = (
            db.query(Agenda)
            .filter_by(atalho=agenda_code, id_empresa=company.id)
            .first()
        )
        if not agenda:
            raise FailedFunctionRunException(
                detail="Agenda not found in the database",
                function_name=add_event_to_agenda.__name__,
            )

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(
                detail="Could not create the agenda client",
                function_name=add_event_to_agenda.__name__,
            )

        status = await agenda_client.add_event(
            agenda_address=agenda.endereco,
            data=date,
            subject=title,
            description=description,
            localization=localization,
        )

    return status
