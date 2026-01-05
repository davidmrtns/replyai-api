from datetime import datetime, timedelta
import asyncio
import pytz

from app.db.database import get_db_session_with_context
from app.db.models import Company
from app.jobs.sub_jobs import (
    enviar_aviso_vencimento,
    enviar_cobranca_inadimplente,
)


def rodar_avisar_vencimento():
    asyncio.run(avisar_vencimento())


def rodar_cobrar_inadimplentes():
    asyncio.run(cobrar_inadimplentes())


async def avisar_vencimento():
    with get_db_session_with_context() as db:
        try:
            empresas = (
                db.query(Company)
                .filter_by(charge_due_payments_is_active=True, is_active=True)
                .all()
            )

            for empresa in empresas:
                timezone = empresa.timezone if empresa.timezone else "UTC"
                tz = pytz.timezone(timezone)

                data_atual = datetime.now(tz)
                data_atual_formatada = data_atual.strftime("%Y-%m-%d")
                dia_seguinte = (data_atual + timedelta(days=1)).strftime("%Y-%m-%d")
                dia_adiante = (data_atual + timedelta(days=3)).strftime("%Y-%m-%d")

                await enviar_aviso_vencimento(
                    dia_seguinte, data_atual_formatada, empresa, db
                )
                await enviar_aviso_vencimento(
                    dia_adiante, data_atual_formatada, empresa, db
                )
        except Exception as e:
            print(f"Erro ao processar: {e}")


async def cobrar_inadimplentes():
    with get_db_session_with_context() as db:
        try:
            empresas = (
                db.query(Company)
                .filter_by(charge_due_payments_is_active=True, is_active=True)
                .all()
            )

            for empresa in empresas:
                timezone = empresa.timezone if empresa.timezone else "UTC"
                tz = pytz.timezone(timezone)

                data_atual = datetime.now(tz).strftime("%Y-%m-%d")

                await enviar_cobranca_inadimplente(data_atual, empresa, db)
        except Exception as e:
            print(f"Erro ao processar: {e}")
