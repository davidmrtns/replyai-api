from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.clients.digisac_client import DigisacClient
from app.db.models import Department, DigisacClient as DigisacClientDB
from app.schemas.digisac_client_schema import (
    CreateDepartmentSchema,
    CreateDigisacClientSchema,
    UpdateDigisacClientSchema,
)
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


async def _get_digisac_client(
    digisac_client_id: int, company_id: int | None, db: Session
):
    digisac_client_db = await get_resource_from_db(
        DigisacClientDB, digisac_client_id, db, company_id
    )

    return DigisacClient(
        digisac_slug=digisac_client_db.digisac_slug,
        service_id=digisac_client_db.service_id,
        default_user_id=digisac_client_db.default_user_id,
        digisac_token=digisac_client_db.digisac_token,
    )


async def _get_department_from_db(
    digisac_client_id: int, company_id: int | None, department_id: int, db: Session
):
    digisac_client_db = await get_resource_from_db(
        DigisacClientDB, digisac_client_id, db, company_id
    )

    department = (
        db.query(Department)
        .filter_by(id=department_id, digisac_client_id=digisac_client_db.id)
        .first()
    )
    if not department:
        raise HTTPException(
            status_code=404, detail="Department not found for this Digisac client"
        )

    return department


async def create_digisac_client(
    company_id: int, payload: CreateDigisacClientSchema, db: Session
):
    digisac_client_db = (
        db.query(DigisacClientDB).filter_by(company_id=company_id).first()
    )
    if digisac_client_db:
        raise HTTPException(
            status_code=409,
            detail="This company already has a Digisac client registered",
        )

    digisac_client = DigisacClientDB(
        digisac_slug=payload.digisac_slug,
        service_id=payload.service_id,
        digisac_token=encrypt_api_key(payload.digisac_token),
        default_user_id=payload.default_user_id,
        company_id=company_id,
    )

    db.add(digisac_client)
    db.commit()
    db.refresh(digisac_client)
    return digisac_client


async def update_digisac_client(
    digisac_client_id: int,
    payload: UpdateDigisacClientSchema,
    company_id: int | None,
    db: Session,
):
    update_data = payload.model_dump(exclude_unset=True)

    if "digisac_token" in update_data:
        update_data["digisac_token"] = encrypt_api_key(update_data["digisac_token"])

    digisac_client_db = await get_resource_from_db(
        DigisacClientDB, digisac_client_id, db, company_id
    )

    apply_model_update(digisac_client_db, update_data)
    db.commit()
    return digisac_client_db


async def list_services(
    digisac_client_id: int,
    company_id: int | None,
    page: int,
    service_name: str | None,
    service_id: str | None,
    db: Session,
):
    digisac_client = await _get_digisac_client(digisac_client_id, company_id, db)
    response = digisac_client.list_services(page, service_name, service_id)
    return response


async def list_users(
    digisac_client_id: int,
    company_id: int | None,
    page: int,
    user_name: str | None,
    user_id: str | None,
    db: Session,
):
    digisac_client = await _get_digisac_client(digisac_client_id, company_id, db)
    response = digisac_client.list_users(page, user_name, user_id)
    return response


async def list_departments(
    digisac_client_id: int,
    company_id: int | None,
    page: int,
    department_name: str | None,
    department_id: str | None,
    db: Session,
):
    digisac_client = await _get_digisac_client(digisac_client_id, company_id, db)
    response = digisac_client.list_departments(page, department_name, department_id)
    return response


async def create_department(
    digisac_client_id: int,
    payload: CreateDepartmentSchema,
    company_id: int | None,
    db: Session,
):
    digisac_client_db = await get_resource_from_db(
        DigisacClientDB, digisac_client_id, db, company_id
    )

    department = Department(
        shortcut=payload.shortcut,
        contact_transfer_comment=payload.contact_transfer_comment,
        digisac_department_id=payload.digisac_department_id,
        digisac_user_id=payload.digisac_user_id,
        is_confirmation_department=payload.is_confirmation_department,
        digisac_client_id=digisac_client_db.id,
    )

    db.add(department)
    db.commit()
    db.refresh(department)
    return department


async def update_department(
    digisac_client_id: int,
    department_id: int,
    payload: UpdateDigisacClientSchema,
    company_id: int | None,
    db: Session,
):
    department = await _get_department_from_db(
        digisac_client_id, company_id, department_id, db
    )
    apply_model_update(department, payload)
    db.commit()
    return department


async def delete_department(
    digisac_client_id: int,
    department_id: int,
    company_id: int | None,
    db: Session,
):
    department = await _get_department_from_db(
        digisac_client_id, company_id, department_id, db
    )
    db.delete(department)
    db.commit()
    return True
