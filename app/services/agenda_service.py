import json
import pytz
from sqlalchemy.orm import Session

from app.db.models import Agenda, Assistant, Company
from app.schemas.agenda_schema import CreateAgendaSchema, UpdateAgendaSchema
from app.services import RespostaConfirmacao
from app.clients.assistants_client import AssistantsClient
from app.utils.model_utils import apply_model_update, get_resource_from_db


# TODO: check if this function is still needed or if it can be replaced by an assistant action
async def extract_event_data(
    agenda: str, evento: dict, data_atual: str, empresa: Company, db: Session
):
    instrucao = {
        "acao": "extrair_dados_evento",
        "dados": {
            "email_agenda": agenda,
            "titulo": evento.get("subject", ""),
            "local": evento.get("location", ""),
            "data_hora_inicio": evento.get("start").get("date_time"),
            "data_hora_fim": evento.get("end").get("date_time"),
            "data_hora_atual": data_atual,
        },
    }

    assistente_db = (
        db.query(Assistant)
        .filter_by(proposito="agendar", id_empresa=empresa.id)
        .first()
    )

    try:
        if assistente_db is not None:
            assistente = AssistantsClient(
                assistant_name=assistente_db.nome,
                openai_assistant_id=assistente_db.assistantId,
                openai_api_key=empresa.openai_api_key,
            )
            assistente.add_message(message=json.dumps(instrucao))
            resposta, thread_id = assistente.create_or_run_thread()
            resposta_obj = RespostaConfirmacao.from_dict(json.loads(resposta))
            return resposta_obj, thread_id
    except Exception as e:
        print(e)
    return {}, None


async def create_agenda(payload: CreateAgendaSchema, company_id: int, db: Session):
    agenda = Agenda(
        address=payload.address,
        shortcut=payload.shortcut,
        company_id=company_id,
    )

    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda


async def update_agenda(
    agenda_id: int, request: UpdateAgendaSchema, company_id: int | None, db: Session
):
    agenda = await get_resource_from_db(Agenda, agenda_id, db, company_id)

    apply_model_update(agenda, request)
    db.commit()
    db.refresh(agenda)
    return agenda


async def delete_agenda(agenda_id: int, company_id: int | None, db: Session):
    agenda = await get_resource_from_db(Agenda, agenda_id, db, company_id)

    if agenda:
        db.delete(agenda)
        db.commit()
        return True
    return False


async def list_timezones():
    return {"timezones": pytz.all_timezones}
