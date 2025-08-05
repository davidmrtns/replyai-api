import json

from sqlalchemy.orm import Session

from app.db.models import AsaasClient
from app.db.new_models import Assistant, Company
from app.utils.asaas import Asaas
from app.utils.assistant import Assistant, Instrucao, RespostaFinanceiro


async def extrair_dados_cobranca(
        acao: str,
        nome_cliente: str,
        telefone: str,
        data_atual: str,
        data_vencimento: str,
        descricao_boleto: str,
        empresa: Company,
        db: Session
):
    instrucao = Instrucao(
        acao=acao,
        dados={
            "nome_cliente": nome_cliente,
            "telefone": telefone,
            "data_vencimento": data_vencimento,
            "data_atual": data_atual,
            "descricao_boleto": descricao_boleto
        }
    )

    assistente_db = db.query(Assistant).filter_by(proposito="cobrar", id_empresa=empresa.id).first()

    try:
        if assistente_db is not None:
            assistente = Assistant(nome=assistente_db.nome, id=assistente_db.assistantId, api_key=empresa.openai_api_key)
            assistente.adicionar_mensagens(mensagens=[instrucao.__str__()], id_arquivos=[], thread_id=None)
            resposta, thread_id = assistente.criar_rodar_thread()
            resposta_obj = RespostaFinanceiro.from_dict(json.loads(resposta))
            return resposta_obj, thread_id
    except Exception as e:
        print(e)
    return {}, None


def criar_financial_client(empresa: Company, db: Session, client_number: int | None = None):
    clients = []

    if empresa.financial_client_type == "asaas":
        if client_number is not None:
            asaas_client_db = db.query(AsaasClient).filter_by(id_empresa=empresa.id, client_number=client_number).all()
        else:
            asaas_client_db = db.query(AsaasClient).filter_by(id_empresa=empresa.id).all()

        for client in asaas_client_db:
            clients.append(
                Asaas(token=client.token)
            )

    if clients:
        if client_number is not None:
            return clients[0]
        else:
            return clients
