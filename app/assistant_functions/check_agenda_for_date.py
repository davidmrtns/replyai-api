from openai.types.beta import FunctionToolParam

from app.assistant_functions import _get_variables, _schedule_to_list
from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao


def check_agenda_for_date_doc():
    return FunctionToolParam(
        function={
            "name": "check_agenda_for_date",
            "description": "Gets the availability of a given agenda in a given date",
            "strict": False,
            "parameters": {
                "type": "object",
                "properties": {
                    "agenda_code": {
                        "type": "string",
                        "description": "The agenda code, as chosen by the user"
                    },
                    "suggestion_date": {
                        "type": "string",
                        "description": "The date suggested by the user, in the format DD-MM-YYYYTHH:MM:SS"
                    }
                },
                "additionalProperties": False,
                "required": [
                    "agenda_code",
                    "suggestion_date"
                ]
            }
        },
        type="function"
    )


@register_function(check_agenda_for_date_doc())
async def check_agenda_for_date(
        assistant_id: str,
        agenda_code: str,
        suggestion_date: str
): # TODO: add return typing
    date_info = {
        "status": "unavaliable",
        "schedule": []
    }

    with retornar_sessao() as db:
        company, _, agenda_client, agenda = await _get_variables(assistant_id, agenda_code, db)

        schedules = await agenda_client.obter_horarios(agendas=[agenda.endereco], data=suggestion_date) # TODO: enhance variable names
        if schedules.length < 1:
            return date_info

        first_agenda_schedule = schedules[0]
        if first_agenda_schedule is None:
            return date_info

        if set(first_agenda_schedule.availability_view) == {"2"}:
            date_info["status"] = "closed_all_day"
        else:
            date_info["status"] = "available"
            date_info["schedule"] = _schedule_to_list(first_agenda_schedule, company)
    
    return date_info
