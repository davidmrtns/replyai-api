import json

from sqlalchemy.orm import Session

from app.db.new_models import Contact, Company
from app.services.agendamento_service import verificar_data_sugerida, cadastrar_evento, obter_nova_data_reagendamento, \
    obter_titulo_agenda_evento
from app.services.contato_service import encerrar_contato, atualizar_assistente_atual_contato, transferir_contato, \
    mudar_aguardando_humano
from app.services.crm_service import mover_lead
from app.services.empresa_service import obter_assistente, obter_endereco_agenda, obter_departamento
from app.services.mensagem_service import enviar_mensagem
from app.services.thread_service import executar_thread
from app.utils.agenda_client import AgendaClient
from app.utils.assistant import Resposta, Assistant
from app.utils.crm_client import CRMClient
from app.utils.digisac import Digisac
from app.utils.message_client import MessageClient


async def direcionar(
        resposta: Resposta,
        audio: bool,
        message_client: MessageClient,
        agenda_client: AgendaClient | None,
        crm_client: CRMClient | None,
        empresa: Company,
        contato: Contact,
        assistente: Assistant,
        db: Session
):
    match resposta.atividade:
        case "R": # responder o contato
            await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
        case "T": # transferir o contato
            if isinstance(message_client, Digisac):
                departamento = await obter_departamento(empresa, resposta.departamento, False, db)
                if departamento:
                    await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
                    await mudar_aguardando_humano(contato, True, db)
                    await transferir_contato(message_client, contato, departamento)
        case "E": # encerrar o contato
            await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
            await encerrar_contato(contato, message_client, db)
        case "M": # transferir para outro agente de IA
            await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
            assistente, id_assistente_db = await obter_assistente(empresa, None, resposta.assistente, db)
            if assistente:
                resposta_assistente = await executar_thread(None, None, contato, None, assistente, db)
                await atualizar_assistente_atual_contato(contato, id_assistente_db, db)
                await enviar_mensagem(resposta_assistente.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
        case "AG": # checar agenda
            if agenda_client is not None:
                agenda = await obter_endereco_agenda(empresa, resposta.agenda, db)
                if agenda:
                    mensagem = await verificar_data_sugerida(agenda_client, contato, agenda.endereco, empresa, db)
                    if mensagem:
                        await enviar_mensagem(mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
        case "AG-OK": # incluir evento na agenda
            if agenda_client is not None:
                agenda = await obter_endereco_agenda(empresa, resposta.agenda, db)
                if agenda:
                    mensagem = await cadastrar_evento(agenda_client, contato, agenda.endereco, empresa, db)
                    await mover_lead(crm_client, contato, empresa, resposta.atividade, db)
                    if mensagem:
                        await enviar_mensagem(mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
        case "AG-RE": # reagendar o evento
            if agenda_client is not None:
                data_nova = await obter_nova_data_reagendamento(contato.threadId, empresa, db)
                if data_nova:
                    dados = await obter_titulo_agenda_evento(assistente, contato, data_nova)
                    if dados:
                        if await agenda_client.reagendar_evento(dados):
                            await mover_lead(crm_client, contato, empresa, resposta.atividade, db)
                            await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
                            await encerrar_contato(contato, message_client, db)
        case "AG-CN": # cancelar o evento
            if agenda_client is not None:
                dados = await obter_titulo_agenda_evento(assistente, contato)
                if dados:
                    if await agenda_client.cancelar_evento(dados, empresa.tipo_cancelamento_evento):
                        await mover_lead(crm_client, contato, empresa, resposta.atividade, db)
                        await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
                        await encerrar_contato(contato, message_client, db)
        case "AG-CF": # confirmar o evento
            if agenda_client is not None:
                dados = await obter_titulo_agenda_evento(assistente, contato)
                if dados:
                    if await agenda_client.confirmar_evento(dados):
                        await mover_lead(crm_client, contato, empresa, resposta.atividade, db)
                        await enviar_mensagem(resposta.mensagem, audio, resposta.midia, contato, empresa, message_client, assistente, db)
                        await encerrar_contato(contato, message_client, db)
