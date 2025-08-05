import json

from sqlalchemy.orm import Session

from app.db.new_models import Contact
from app.utils.assistant import Assistant, Resposta
from app.utils.message_client import DadosContato


async def executar_thread(
        mensagem: str | None,
        imagem: str | None,
        contato: Contact,
        dados_contato: DadosContato | None,
        assistente: Assistant,
        db: Session
):
    if mensagem:
        assistente.adicionar_mensagens([mensagem], [], contato.threadId or None)

    if dados_contato:
        assistente.adicionar_mensagens([dados_contato.__str__()], [], contato.threadId or None)

    if imagem:
        id_imagens = assistente.subir_imagens([imagem])
        assistente.adicionar_imagens(id_imagens, contato.threadId or None)

    resposta, thread_id = assistente.criar_rodar_thread(thread_id=contato.threadId)

    if not contato.threadId:
        contato.threadId = thread_id
        db.commit()

    resposta = json.loads(resposta)
    resposta_obj = Resposta.from_dict(resposta)
    return resposta_obj
