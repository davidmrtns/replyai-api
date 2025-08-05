from datetime import datetime, timedelta
import asyncio
import pytz
from sqlalchemy import or_, and_

from app.db.database import retornar_sessao
from app.db.new_models import Company, Contact
from app.jobs.sub_jobs import enviar_retomada_conversa, enviar_confirmacao_consulta, enviar_aviso_vencimento, \
    enviar_cobranca_inadimplente


def rodar_retomar_conversa():
    asyncio.run(retomar_conversa())

def rodar_confirmar_agendamento():
    asyncio.run(confirmar_agendamento())

def rodar_avisar_vencimento():
    asyncio.run(avisar_vencimento())

def rodar_cobrar_inadimplentes():
    asyncio.run(cobrar_inadimplentes())


async def retomar_conversa():
    agora = datetime.now()

    with retornar_sessao() as db:
        try:
            empresas = db.query(Company).filter_by(recall_is_active=True, is_active=True).all()

            for empresa in empresas:
                timeout_padrao = empresa.recall_timeout_minutes or 60
                timeout_padrao_time = agora - timedelta(minutes=timeout_padrao)

                timeout_final = empresa.final_recall_timeout_minutes or 1440
                timeout_final_time = agora - timedelta(minutes=timeout_final)

                query = db.query(Contact).filter(
                    Contact.company_id == empresa.id,
                    or_(
                        and_(
                            Contact.last_message_at <= timeout_padrao_time,
                            Contact.recall_count < empresa.recall_quant - 1,
                            Contact.receive_ai_replies == True,
                            Contact.awaiting_human_contact == False
                        ),
                        and_(
                            Contact.last_message_at <= timeout_final_time,
                            Contact.recall_count == empresa.recall_quant - 1,
                            Contact.receive_ai_replies == True,
                            Contact.awaiting_human_contact == False
                        )
                    )
                )

                if not empresa.recall_confirmacao_ativo:
                    query = query.filter_by(appointment_confirmation_is_active=False)

                interacoes_inativas = query.all()

                for contato in interacoes_inativas:
                    await enviar_retomada_conversa(contato, empresa, db)
        except Exception as e:
            print(f"Erro ao processar: {e}")


async def confirmar_agendamento():
    with retornar_sessao() as db:
        try:
            empresas = db.query(Company).filter_by(appointment_confirmation_is_active=True, is_active=True).all()

            for empresa in empresas:
                timezone = empresa.timezone if empresa.timezone else "UTC"
                tz = pytz.timezone(timezone)

                data_atual = datetime.now(tz)
                data_atual_formatada = data_atual.strftime("%Y-%m-%dT%H:%M:%S")
                dia_seguinte = (data_atual + timedelta(days=1)).strftime("%Y-%m-%d")

                await enviar_confirmacao_consulta(dia_seguinte, data_atual_formatada, empresa, db)
        except Exception as e:
            print(f"Erro ao processar: {e}")


async def avisar_vencimento():
    with retornar_sessao() as db:
        try:
            empresas = db.query(Company).filter_by(charge_due_payments_is_active=True, is_active=True).all()

            for empresa in empresas:
                timezone = empresa.timezone if empresa.timezone else "UTC"
                tz = pytz.timezone(timezone)

                data_atual = datetime.now(tz)
                data_atual_formatada = data_atual.strftime("%Y-%m-%d")
                dia_seguinte = (data_atual + timedelta(days=1)).strftime("%Y-%m-%d")
                dia_adiante = (data_atual + timedelta(days=3)).strftime("%Y-%m-%d")

                await enviar_aviso_vencimento(dia_seguinte, data_atual_formatada, empresa, db)
                await enviar_aviso_vencimento(dia_adiante, data_atual_formatada, empresa, db)
        except Exception as e:
            print(f"Erro ao processar: {e}")


async def cobrar_inadimplentes():
    with retornar_sessao() as db:
        try:
            empresas = db.query(Company).filter_by(charge_due_payments_is_active=True, is_active=True).all()

            for empresa in empresas:
                timezone = empresa.timezone if empresa.timezone else "UTC"
                tz = pytz.timezone(timezone)

                data_atual = datetime.now(tz).strftime("%Y-%m-%d")

                await enviar_cobranca_inadimplente(data_atual, empresa, db)
        except Exception as e:
            print(f"Erro ao processar: {e}")
