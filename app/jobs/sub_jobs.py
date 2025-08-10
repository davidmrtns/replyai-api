from sqlalchemy.orm import Session

from app.db.new_models import Contact, Company
from app.db.models import Agenda
from app.services.agenda_service import create_agenda_client
from app.services.agendamento_service import extrair_dados_evento
from app.services.cobranca_service import extrair_dados_cobranca, criar_financial_client
from app.services.company_service import get_assistant_from_company, get_department
from app.services.contato_service import redefinir_contato, obter_criar_contato, atualizar_thread_contato, \
    atualizar_assistente_atual_contato, transferir_contato, obter_id_contato
from app.services.direcionamento_service import direcionar # TODO: update to use the new pipelines
from app.services.mensagem_service import criar_message_client
from app.services.thread_service import execute_thread
from app.utils.digisac import Digisac
from app.utils.financial_client import FinancialClient
from app.utils.message_client import MessageClient


async def enviar_retomada_conversa(contato: Contact, empresa: Company, db: Session):
    try:
        assistente, _ = await get_assistant_from_company(empresa, "retomar", None, db)

        if not assistente:
            return

        if contato.recallCount < empresa.recall_quant - 1:
            acao = "retomar_atendimento"
        else:
            acao = "encerrar_conversa"

        message_client = criar_message_client(empresa, db)
        if isinstance(message_client, Digisac):
            ticket_id, last_message_id = message_client.obter_ticket_ultima_mensagem(contato.contactId)
            if ticket_id is None:
                await redefinir_contato(contato, db)
                return
            else:
                if last_message_id is None:
                    return
                origem_mensagem = message_client.obter_origem_mensagem(last_message_id)
                if origem_mensagem is None or origem_mensagem == "user":
                    await redefinir_contato(contato, db)
                    return
        resposta = await execute_thread(acao, None, contato, assistente, db)
        await direcionar(resposta, False, message_client, None, None, empresa, contato, assistente, db)

        if resposta.atividade != "E":
            contato.recallCount += 1
        db.commit()
        return
    except Exception as e:
        db.rollback()
        print(f"Erro ao enviar retomada de conversa para o contato de ID {contato.id}: {e}")


async def enviar_confirmacao_consulta(data: str, data_atual: str, empresa: Company, db: Session):
    agenda_client = create_agenda_client(empresa, db)
    agendas = db.query(Agenda).filter_by(id_empresa=empresa.id).all()

    message_client = criar_message_client(empresa, db)
    respostas = await agenda_client.obter_horarios(agendas=[agenda.endereco for agenda in agendas], data=data)

    for resposta in respostas:
        for evento in resposta.schedule_items:
            try:
                resposta_extracao, thread_id = await extrair_dados_evento(resposta.schedule_id, evento, data_atual, empresa, db)
                if resposta_extracao:
                    if resposta_extracao.telefone:
                        try:
                            id_contato = await obter_id_contato(message_client, resposta_extracao.telefone, resposta_extracao.cliente)
                            if id_contato:
                                contato = (await obter_criar_contato(None, id_contato, empresa, message_client, None, db))[0]
                                assistente, assistente_db_id = await get_assistant_from_company(empresa, "confirmar", None, db)
                                if assistente:
                                    if not contato.appointmentConfirmation:
                                        contato.appointmentConfirmation = True
                                        db.commit()
                                        await atualizar_assistente_atual_contato(contato, assistente_db_id, db)
                                    if isinstance(message_client, Digisac):
                                        message_client.encerrar_chamado(contactId=contato.contactId, ticketTopicIds=[], comments="Chamado encerrado para confirmação de consulta", byUserId=None)
                                        departamento = await get_department(empresa, None, True, db)
                                        if departamento:
                                            await transferir_contato(message_client, contato, departamento)
                                    await direcionar(resposta_extracao.resposta_confirmacao, False, message_client, None, None, empresa, contato, assistente, db)
                                    await atualizar_thread_contato(contato, thread_id, db)
                        except Exception as e:
                            db.rollback()
                            print(f"Erro ao processar contato {resposta_extracao.cliente} - {resposta_extracao.telefone}: {e}")
            except Exception as e:
                db.rollback()
                print(f"Erro ao processar evento {evento}: {e}")


async def enviar_aviso_vencimento(data_cobranca: str, data_atual: str, empresa: Company, db: Session):
    message_client = criar_message_client(empresa, db)
    financial_clients = criar_financial_client(empresa, db)

    for financial_client in financial_clients:
        resposta = financial_client.listar_cobrancas(due_date_le=data_cobranca, due_date_ge=data_cobranca, status="PENDING", limit="100")
        if resposta.get("totalCount", 0) > 0:
            for cobranca in resposta.get("data", []):
                await processar_cobranca("extrair_dados_aviso_vencimento", cobranca, data_atual, empresa.enviar_boleto_lembrar_vencimento, empresa, message_client, financial_client, db)


async def enviar_cobranca_inadimplente(data: str, empresa: Company, db: Session):
    message_client = criar_message_client(empresa, db)
    financial_clients = criar_financial_client(empresa, db)

    for financial_client in financial_clients:
        resposta = financial_client.listar_cobrancas(status="OVERDUE", limit="100")
        if resposta.get("totalCount", 0) > 0:
            for cobranca in resposta.get("data", []):
                await processar_cobranca("extrair_dados_inadimplencia", cobranca, data, False, empresa, message_client, financial_client, db)


async def processar_cobranca(acao: str, cobranca: dict, data_atual: str, enviar_boleto: bool, empresa: Company, message_client: MessageClient, financial_client: FinancialClient, db: Session):
    try:
        cliente = financial_client.obter_cliente(id_cliente=cobranca.get("customer", ""))
        if cliente:
            telefone = cliente.get("mobilePhone", "")
            nome = cliente.get("name", "")
            data_vencimento = cobranca.get("dueDate", "")
            descricao_boleto = cobranca.get("description", "")
            resposta_vencimento, thread_id = await extrair_dados_cobranca(acao, nome, telefone, data_atual, data_vencimento,
                                                                          descricao_boleto, empresa, db)

            if resposta_vencimento:
                assistente, assistente_db_id = await get_assistant_from_company(empresa, "cobrar", None, db)
                id_contato = await obter_id_contato(message_client, resposta_vencimento.telefone, nome)
                contato = (await obter_criar_contato(None, id_contato, empresa, message_client, None, db))[0]
                await atualizar_assistente_atual_contato(contato, assistente_db_id, db)
                await direcionar(resposta_vencimento.resposta, False, message_client, None, None, empresa, contato,
                                 assistente, db)

                if enviar_boleto:
                    url_boleto = cobranca.get("bankSlipUrl", "")
                    if url_boleto:
                        boleto = message_client.baixar_arquivo(url_boleto)
                        if boleto:
                            mediatype = "application/pdf" if isinstance(message_client, Digisac) else "document"
                            message_client.enviar_mensagem(mensagem="", base64=boleto, mediatype=mediatype, nome_arquivo="boleto.pdf", contact_id=contato.contactId, userId=None, origin="bot", nome_assistente=assistente.nome)

                await atualizar_thread_contato(contato, thread_id, db)
    except Exception as e:
        db.rollback()
        print(f"Erro ao processar cobrança da empresa de ID {empresa.id}: {e}")


async def processar_nf(acao: str, nota: dict, data_atual: str, empresa: Company, message_client: MessageClient, financial_client: FinancialClient, db: Session):
    try:
        cliente = financial_client.obter_cliente(id_cliente=nota.get("customer", ""))
        if cliente:
            telefone = cliente.get("mobilePhone", "")
            nome = cliente.get("name", "")
            url_nota = nota.get("pdfUrl", "")
            if url_nota:
                documento = message_client.baixar_arquivo(url_nota)
                if documento:
                    resposta_vencimento, thread_id = await extrair_dados_cobranca(acao, nome, telefone, data_atual, "",
                                                                                  "", empresa, db)
                    if resposta_vencimento:
                        assistente, assistente_db_id = await get_assistant_from_company(empresa, "cobrar", None, db)
                        id_contato = await obter_id_contato(message_client, resposta_vencimento.telefone, nome)
                        contato = (await obter_criar_contato(None, id_contato, empresa, message_client, None, db))[0]
                        await atualizar_assistente_atual_contato(contato, assistente_db_id, db)
                        await direcionar(resposta_vencimento.resposta, False, message_client, None, None, empresa, contato,
                                         assistente, db)

                        mediatype = "application/pdf" if isinstance(message_client, Digisac) else "document"
                        message_client.enviar_mensagem(mensagem="", base64=documento, mediatype=mediatype, nome_arquivo="nota_fiscal.pdf", contact_id=contato.contactId, userId=None, origin="bot", nome_assistente=assistente.nome)

                        await atualizar_thread_contato(contato, thread_id, db)
    except Exception as e:
        db.rollback()
        print(f"Erro ao processar NF da empresa de ID {empresa.id}: {e}")
