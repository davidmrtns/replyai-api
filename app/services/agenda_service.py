import json
from sqlalchemy.orm import Session

from app.db.new_models import Assistant, Company
from app.services import RespostaConfirmacao
from app.clients.assistants_client import AssistantsClient


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
