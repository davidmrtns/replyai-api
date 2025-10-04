from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.models import Agenda
from app.db.new_models import Assistant, Company
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client


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
        thread_id: str,
        agenda_code: str,
        suggestion_date: str
): # TODO: add return typing
    date_info = {
        "status": "unavaliable",
        "schedule": []
    }

    with retornar_sessao() as db:
        assistant = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        if not assistant:
            raise FailedFunctionRunException(detail='Assistant not found in the database', function_name=check_agenda_for_date.__name__)
        
        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(detail='Company not found in the database', function_name=check_agenda_for_date.__name__)

        agenda = db.query(Agenda).filter_by(atalho=agenda_code, id_empresa=company.id).first()
        if not agenda:
            raise FailedFunctionRunException(detail='Agenda not found in the database', function_name=check_agenda_for_date.__name__)

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(detail='Could not create the agenda client', function_name=check_agenda_for_date.__name__)

        schedules = await agenda_client.get_schedules(agendas=[agenda.endereco], date=suggestion_date)
        if len(schedules) < 1:
            return date_info

        first_agenda_schedule = schedules[0]
        if first_agenda_schedule is None:
            return date_info

        if set(first_agenda_schedule.availability_view) == {'2'}:
            date_info['status'] = 'closed_all_day'
        else:
            date_info['status'] = 'available'
            date_info['schedule'] = first_agenda_schedule.to_string_list(company)
    
    return date_info
