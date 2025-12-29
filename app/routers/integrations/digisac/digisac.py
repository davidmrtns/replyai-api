from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Company, Department
from app.db.models import DigisacClient as DigisacClientDB
from app.routers.integrations.digisac.digisac_helpers import (
    get_department_from_db,
    get_digisac_client,
    get_digisac_client_from_db,
)
from app.routers.routers_helpers import check_company_access
from app.schemas.digisac_client_schema import (
    CreateDepartmentSchema,
    CreateDigisacClientSchema,
    DepartmentSchema,
    DigisacClientSchema,
    UpdateDepartmentSchema,
    UpdateDigisacClientSchema,
)
from app.utils.api_key_encryption import encrypt_api_key


router = APIRouter()


@router.post("/{company_slug}", response_model=DigisacClientSchema)
async def create_digisac_client(
    company_slug: str,
    request: CreateDigisacClientSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = await get_digisac_client_from_db(company, db)
    if digisac_client_db:
        raise HTTPException(
            status_code=404,
            detail="This company already has a Digisac client registered",
        )

    digisac_client = DigisacClientDB(
        digisac_slug=request.digisac_slug,
        service_id=request.service_id,
        digisac_token=encrypt_api_key(request.digisac_token),
        digisac_default_user=request.digisac_default_user,
        company_id=company.id,
    )

    db.add(digisac_client)
    db.commit()
    db.refresh(digisac_client)
    return digisac_client


@router.put("/{company_slug}", response_model=DigisacClientSchema)
async def update_digisac_client(
    company_slug: str,
    request: UpdateDigisacClientSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = await get_digisac_client_from_db(company, db)

    digisac_client_db.digisac_slug = request.digisac_slug
    digisac_client_db.digisac_token = encrypt_api_key(request.digisac_token)
    digisac_client_db.digisac_default_user = request.digisac_default_user
    digisac_client_db.service_id = request.service_id

    db.commit()
    return digisac_client_db


@router.get("/{company_slug}/services")
async def list_digisac_services(
    company_slug: str,
    page: int = 1,
    service_name: str = None,
    service_id: str = None,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)
    digisac_client = get_digisac_client(digisac_client_db)

    response = digisac_client.list_services(page, service_name, service_id)
    return response


@router.get("/{company_slug}/users")
async def list_digisac_users(
    company_slug: str,
    page: int = 1,
    user_name: str = None,
    user_id: str = None,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)
    digisac_client = get_digisac_client(digisac_client_db)

    response = digisac_client.list_users(page, user_name, user_id)
    return response


@router.get("/{company_slug}/departments")
async def list_digisac_departments(
    company_slug: str,
    page: int = 1,
    department_name: str = None,
    department_id: str = None,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)
    digisac_client = get_digisac_client(digisac_client_db)

    response = digisac_client.list_departments(page, department_name, department_id)
    return response


@router.post("/{company_slug}/departments", response_model=DepartmentSchema)
async def create_department(
    company_slug: str,
    request: CreateDepartmentSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = await get_digisac_client_from_db(company, db)

    department = Department(
        shortcut=request.shortcut,
        contact_transfer_comment=request.contact_transfer_comment,
        digisac_department_id=request.digisac_department_id,
        digisac_user_id=request.digisac_user_id,
        is_confirmation_department=request.is_confirmation_department,
        digisac_client_id=digisac_client_db.id,
    )

    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put(
    "/{company_slug}/departments/{department_id}",
    response_model=DepartmentSchema,
)
async def edit_department(
    company_slug: str,
    department_id: int,
    request: UpdateDepartmentSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = await get_digisac_client_from_db(company, db)
    department = get_department_from_db(digisac_client_db, department_id, db)

    department.shortcut = request.shortcut
    department.contact_transfer_comment = request.contact_transfer_comment
    department.digisac_department_id = request.digisac_department_id
    department.digisac_user_id = request.digisac_user_id
    department.is_confirmation_department = request.is_confirmation_department
    db.commit()
    return department


@router.delete("/{company_slug}/departments/{department_id}")
async def delete_department(
    company_slug: str,
    department_id: int,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = await get_digisac_client_from_db(company, db)
    department = get_department_from_db(digisac_client_db, department_id, db)

    db.delete(department)
    db.commit()
    return True
