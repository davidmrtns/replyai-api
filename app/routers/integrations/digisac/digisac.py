from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Company, Department
from app.db.models import DigisacClient as DigisacClientDB
from app.routers.empresa import verificar_permissao_empresa
from app.routers.integrations.digisac.digisac_helpers import (
    get_department_from_db,
    get_digisac_client,
    get_digisac_client_from_db,
)
from app.routers.routers_helpers import check_company_access
from app.schemas.integrations_schemas import (
    DigisacClientSchema,
    DigisacDepartmentSchema,
)
from app.schemas.empresa_schema import (
    DigisacClientSchema as DigisacClientSchemaEmpresa,
    DepartamentoSchema as DigisacDepartmentSchemaEmpresa,
)
from app.utils.api_key_encryption import encrypt_api_key


router = APIRouter()


@router.get("/{company_slug}/services")
async def list_services(
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
async def list_users(
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
async def list_departments(
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


@router.post("/{company_slug}/departments")
async def create_department(
    company_slug: str,
    request: DigisacDepartmentSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)

    department = Department(
        shortcut=request.atalho,
        contact_transfer_comment=request.comentario,
        digisac_department_id=request.department_id,
        digisac_user_id=request.user_id,
        is_confirmation_department=request.departamento_confirmacao,
        digisac_client_id=digisac_client_db.id,
    )

    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.put(
    "/{company_slug}/departments/{department_id}",
    response_model=DigisacDepartmentSchemaEmpresa,
)
async def edit_department(
    company_slug: str,
    department_id: int,
    request: DigisacDepartmentSchema,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)
    department = get_department_from_db(digisac_client_db, db)

    department.atalho = request.atalho
    department.comentario = request.comentario
    department.departmentId = request.department_id
    department.userId = request.user_id
    department.departamento_confirmacao = request.departamento_confirmacao

    db.commit()
    return department


@router.delete("/{company_slug}/departments/{department_id}")
async def delete_department(
    company_slug: str,
    department_id: int,
    company: Company = Depends(check_company_access),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)
    department = get_department_from_db(digisac_client_db, db)

    db.delete(department)
    db.commit()
    return True


@router.post("/{company_slug}")
async def create_digisac_client(
    company_slug: str,
    request: DigisacClientSchema,
    company: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)
    if digisac_client_db:
        raise HTTPException(
            status_code=404,
            detail="This company already has a Digisac client registered",
        )

    digisac_client = DigisacClientDB(
        digisac_slug=request.slug,
        service_id="",
        digisac_token=encrypt_api_key(request.token),
        digisac_default_user="",
        company_id=company.id,
    )

    db.add(digisac_client)
    db.commit()
    db.refresh(digisac_client)
    return digisac_client


@router.put("/{company_slug}", response_model=DigisacClientSchemaEmpresa)
async def edit_digisac_client(
    company_slug: str,
    request: DigisacClientSchema,
    company: Company = Depends(verificar_permissao_empresa),
    db: Session = Depends(obter_sessao),
):
    digisac_client_db = get_digisac_client_from_db(company, db)

    digisac_client_db.digisacSlug = request.slug
    digisac_client_db.digisacToken = encrypt_api_key(request.token)
    digisac_client_db.digisacDefaultUser = request.user_id
    digisac_client_db.service_id = request.service_id

    db.commit()
    return digisac_client_db
