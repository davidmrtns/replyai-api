from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.clients.financial_client import FinancialClient
from app.clients.message_client import MessageClient
from app.db.models import Company
from app.services.billing_service import (
    generate_billing_response,
    create_financial_clients,
)
from app.services.company_service import get_assistant_from_company
from app.services.contact_service import (
    get_or_create_contact,
    update_current_assistant,
)

# from app.services.direcionamento_service import direcionar
from app.utils.create_message_client import create_message_client
from app.services.thread_service import assign_new_thread_to_contact


async def enviar_aviso_vencimento(
    data_cobranca: str, data_atual: str, empresa: Company, db: Session
):
    message_client = create_message_client(empresa, db)
    financial_clients = create_financial_clients(empresa, db)

    for financial_client in financial_clients:
        resposta = financial_client.listar_cobrancas(
            due_date_le=data_cobranca,
            due_date_ge=data_cobranca,
            status="PENDING",
            limit="100",
        )
        if resposta.get("totalCount", 0) > 0:
            for cobranca in resposta.get("data", []):
                await processar_cobranca(
                    "extrair_dados_aviso_vencimento",
                    cobranca,
                    data_atual,
                    empresa.enviar_boleto_lembrar_vencimento,
                    empresa,
                    message_client,
                    financial_client,
                    db,
                )


async def enviar_cobranca_inadimplente(data: str, empresa: Company, db: Session):
    message_client = create_message_client(empresa, db)
    financial_clients = create_financial_clients(empresa, db)

    for financial_client in financial_clients:
        resposta = financial_client.listar_cobrancas(status="OVERDUE", limit="100")
        if resposta.get("totalCount", 0) > 0:
            for cobranca in resposta.get("data", []):
                await processar_cobranca(
                    "extrair_dados_inadimplencia",
                    cobranca,
                    data,
                    False,
                    empresa,
                    message_client,
                    financial_client,
                    db,
                )


async def processar_cobranca(
    acao: str,
    cobranca: dict,
    data_atual: str,
    enviar_boleto: bool,
    empresa: Company,
    message_client: MessageClient,
    financial_client: FinancialClient,
    db: Session,
):
    try:
        cliente = financial_client.get_customer(id_cliente=cobranca.get("customer", ""))
        if cliente:
            telefone = cliente.get("mobilePhone", "")
            nome = cliente.get("name", "")
            data_vencimento = cobranca.get("dueDate", "")
            descricao_boleto = cobranca.get("description", "")
            resposta_vencimento, thread_id = await generate_billing_response(
                acao,
                nome,
                telefone,
                data_atual,
                data_vencimento,
                descricao_boleto,
                empresa,
                db,
            )

            if resposta_vencimento:
                assistente, assistente_db_id = await get_assistant_from_company(
                    empresa, "cobrar", None, db
                )
                id_contato = await message_client.obter_id_contato(
                    resposta_vencimento.telefone, nome
                )
                contato = (
                    await get_or_create_contact(
                        None, id_contato, empresa, message_client, None, db
                    )
                )[0]
                await update_current_assistant(contato, assistente_db_id, db)
                """await direcionar(resposta_vencimento.resposta, False, message_client, None, None, empresa, contato,
                                 assistente, db)"""

                if enviar_boleto:
                    url_boleto = cobranca.get("bankSlipUrl", "")
                    if url_boleto:
                        boleto = message_client.baixar_arquivo(url_boleto)
                        if boleto:
                            mediatype = (
                                "application/pdf"
                                if isinstance(message_client, DigisacClient)
                                else "document"
                            )
                            message_client.enviar_mensagem(
                                mensagem="",
                                base64=boleto,
                                mediatype=mediatype,
                                nome_arquivo="boleto.pdf",
                                contact_id=contato.contactId,
                                userId=None,
                                origin="bot",
                                nome_assistente=assistente.assistant_name,
                            )

                await assign_new_thread_to_contact(contato, thread_id, db)
    except Exception as e:
        db.rollback()
        print(f"Erro ao processar cobrança da empresa de ID {empresa.id}: {e}")


async def processar_nf(
    acao: str,
    nota: dict,
    data_atual: str,
    empresa: Company,
    message_client: MessageClient,
    financial_client: FinancialClient,
    db: Session,
):
    try:
        cliente = financial_client.get_customer(id_cliente=nota.get("customer", ""))
        if cliente:
            telefone = cliente.get("mobilePhone", "")
            nome = cliente.get("name", "")
            url_nota = nota.get("pdfUrl", "")
            if url_nota:
                documento = message_client.baixar_arquivo(url_nota)
                if documento:
                    resposta_vencimento, thread_id = await generate_billing_response(
                        acao, nome, telefone, data_atual, "", "", empresa, db
                    )
                    if resposta_vencimento:
                        assistente, assistente_db_id = await get_assistant_from_company(
                            empresa, "cobrar", None, db
                        )
                        id_contato = await message_client.obter_id_contato(
                            resposta_vencimento.telefone, nome
                        )
                        contato = (
                            await get_or_create_contact(
                                None, id_contato, empresa, message_client, None, db
                            )
                        )[0]
                        await update_current_assistant(contato, assistente_db_id, db)
                        """await direcionar(resposta_vencimento.resposta, False, message_client, None, None, empresa, contato,
                                         assistente, db)"""

                        mediatype = (
                            "application/pdf"
                            if isinstance(message_client, DigisacClient)
                            else "document"
                        )
                        message_client.enviar_mensagem(
                            mensagem="",
                            base64=documento,
                            mediatype=mediatype,
                            nome_arquivo="nota_fiscal.pdf",
                            contact_id=contato.contactId,
                            userId=None,
                            origin="bot",
                            nome_assistente=assistente.assistant_name,
                        )

                        await assign_new_thread_to_contact(contato, thread_id, db)
    except Exception as e:
        db.rollback()
        print(f"Erro ao processar NF da empresa de ID {empresa.id}: {e}")
