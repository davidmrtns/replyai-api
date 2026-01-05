from datetime import datetime
import asyncio
import pytz

from app.db.database import get_db_session_with_context
from app.db.models import Company
from app.jobs.sub_jobs import (
    enviar_cobranca_inadimplente,
)


def rodar_cobrar_inadimplentes():
    asyncio.run(cobrar_inadimplentes())


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
