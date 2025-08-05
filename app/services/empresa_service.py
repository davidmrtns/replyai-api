from sqlalchemy.orm import Session

from app.db.models import Agenda, Departamento
from app.db.new_models import Company, Assistant
from app.db.new_models import DigisacClient
from app.services.agendamento_service import criar_agenda_client
from app.services.crm_service import create_crm_client
from app.services.mensagem_service import criar_message_client
from app.utils.assistant import Assistant


async def obter_empresa(slug: str, token: str, db: Session):
    empresa: Company | None = db.query(Company).filter_by(slug=slug, token=token, empresa_ativa=True).first()

    if empresa is not None:
        message_client = criar_message_client(empresa, db)
        agenda_client = criar_agenda_client(empresa, db)
        crm_client = create_crm_client(empresa, db)
        return empresa, message_client, agenda_client, crm_client
    return None


async def obter_endereco_agenda(empresa: Company, atalho: str, db: Session):
    if empresa is not None:
        agenda = db.query(Agenda).filter_by(atalho=atalho, id_empresa=empresa.id).first()
        return agenda
    return None


async def obter_assistente(empresa: Company, proposito: str | None, atalho: str | None, db: Session):
    if empresa is not None:
        if proposito:
            assistente_db = db.query(Assistant).filter_by(id_empresa=empresa.id, proposito=proposito).first()
        else:
            assistente_db = db.query(Assistant).filter_by(id_empresa=empresa.id, atalho=atalho).first()
        if assistente_db:
            assistente = Assistant(nome=assistente_db.nome, id=assistente_db.assistantId, api_key=empresa.openai_api_key)
            return assistente, assistente_db.id
    return None, None


async def obter_departamento(empresa: Company, atalho: str | None, dpt_confirmacao: bool, db: Session):
    digisac_client_db = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()

    if digisac_client_db is not None:
        if dpt_confirmacao:
            departamento = db.query(Departamento).filter_by(departamento_confirmacao=True, id_digisac_client=digisac_client_db.id).first()
        else:
            departamento = db.query(Departamento).filter_by(atalho=atalho, id_digisac_client=digisac_client_db.id).first()
        if departamento is not None:
            return departamento
    return None
