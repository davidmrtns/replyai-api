from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.db.models import Departamento
from app.db.new_models import Company, DigisacClient as DigisacClientDB


async def get_digisac_client_from_db(
    company: Company, db: Session
) -> DigisacClientDB | None:
    digisac_client_db = (
        db.query(DigisacClientDB).filter_by(company_id=company.id).first()
    )
    if not digisac_client_db:
        raise HTTPException(
            status_code=404, detail="No Digisac client found for this company"
        )
    else:
        return digisac_client_db


def get_department_from_db(
    digisac_client: DigisacClientDB, department_id: int, db: Session
):
    department = (
        db.query(Departamento)
        .filter_by(id=department_id, digisac_client_id=digisac_client.id)
        .first()
    )
    if not department:
        raise HTTPException(
            status_code=404, detail="Department not found for this Digisac client"
        )

    return department


def get_digisac_client(digisac_client_db: DigisacClientDB) -> DigisacClient:
    return DigisacClient(
        digisac_slug=digisac_client_db.digisac_slug,
        service_id=digisac_client_db.service_id,
        default_user_id=digisac_client_db.digisac_default_user,
        digisac_token=digisac_client_db.digisac_token,
    )
