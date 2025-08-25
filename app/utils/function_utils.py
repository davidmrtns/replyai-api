from datetime import datetime
'''from typing_extensions import Literal
from sqlalchemy.orm import Session'''

import pytz

from app.db.database import retornar_sessao
from app.db.models import Colaborador
from app.db.new_models import Assistant, Company, Contact
'''from app.services.agenda_service import create_agenda_client, get_original_event_data, schedule_to_list
from app.services.company_service import get_agenda'''


FUNCTION_REGISTRY = {}


def register(func):
    FUNCTION_REGISTRY[func.__name__] = func
    return func


@register
def get_current_datetime(id_assistente: str, **kwargs):
    timezone = "UTC"

    with retornar_sessao() as db:
        assistente_db = db.query(Assistant).filter_by(assistantId=id_assistente).first()
        if assistente_db:
            empresa = db.query(Company).filter_by(id=assistente_db.id_empresa).first()
            if empresa:
                timezone = empresa.fuso_horario

    tz = pytz.timezone(timezone)
    now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")

    return {"current_datetime": now}


@register
def get_employees(id_assistente: str, **kwargs):
    with retornar_sessao() as db:
        assistente_db = db.query(Assistant).filter_by(assistantId=id_assistente).first()
        if assistente_db:
            empresa = db.query(Company).filter_by(id=assistente_db.id_empresa).first()
            if empresa:
                colaboradores = db.query(Colaborador).filter_by(id_empresa=empresa.id).all()
                data = [
                    {"nome": colab.nome, "apelido": colab.apelido, "departamento": colab.departamento}
                    for colab in colaboradores
                ]

                return {"employees": data}
    return {"employees": ""}


'''async def check_agenda_for_date(
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
            date_info["schedule"] = schedule_to_list(first_agenda_schedule, company)
    
    return date_info


async def add_event_to_agenda(
        assistant_id: str,
        agenda_code: str,
        datetime: str,
        title: str,
        description: str,
        localization: str
) -> bool:
    status = False

    with retornar_sessao() as db:
        company, _, agenda_client, agenda = await _get_variables(assistant_id, agenda_code, db)
        
        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            return status
        
        await agenda_client.cadastrar_evento(agenda=agenda.endereco, data=datetime,
                                                 titulo=title, descricao=description, localizacao=localization)
        status = True # TODO: get the status from the create_event method, when improved
    
    return status


async def reschedule_event(
        assistant_id: str,
        agenda_code: str,
        new_datetime: str,
        contact: Contact,
) -> bool:
    status = False

    with retornar_sessao() as db:
        _, assistant, agenda_client, __ = await _get_variables(assistant_id, agenda_code, db)
        
        original_event_data = await get_original_event_data(assistant, contact)
        if original_event_data is None:
            return status

        original_event_data.start_datetime = new_datetime
        await agenda_client.reagendar_evento(original_event_data) # TODO: update this method to accept new datetime
        status = True # TODO: get the status from the reschedule_event method, when improved
    
    return status


async def cancel_or_confirm_event(
        assistant_id: str,
        agenda_code: str,
        action: Literal['cancel', 'confirm'],
        contact: Contact,
) -> bool:
    status = False

    with retornar_sessao() as db:
        company, assistant, agenda_client, __ = await _get_variables(assistant_id, agenda_code, db)
        
        original_event_data = await get_original_event_data(assistant, contact)
        if original_event_data is None:
            return status

        if action == 'cancel':
            await agenda_client.cancelar_evento(original_event_data, company.event_cancellation_type)
            status = True # TODO: get the status from the cancel_event method, when improved
        elif action == 'confirm':
            await agenda_client.confirmar_evento(original_event_data)
            status = True # TODO: get the status from the confirm_event method, when improved
    
    return status


# TODO: call it a better name and add typing
async def _get_variables(
        assistant_id: str,
        agenda_code: str,
        db: Session,
):
    assistant = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
    
    if assistant is None:
        return None

    company = assistant.company

    agenda = await get_agenda(company, agenda_code, db)
    if agenda is None:
        return None
    
    agenda_client = create_agenda_client(company, db)
    if agenda_client is None:
        return None
    
    return company, assistant, agenda_client, agenda'''
