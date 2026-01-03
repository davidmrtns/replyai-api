from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from ..routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.digisac_client_schema import (
    CreateDepartmentSchema,
    CreateDigisacClientSchema,
    DepartmentSchema,
    DigisacClientSchema,
    UpdateDepartmentSchema,
    UpdateDigisacClientSchema,
)
from app.services.digisac_service import (
    create_digisac_client as create_digisac_client_service,
    update_digisac_client as update_digisac_client_service,
    list_departments,
    list_services,
    list_users,
    create_department as create_department_service,
    update_department as update_department_service,
    delete_department as delete_department_service,
)


router = APIRouter()


@router.post("/", response_model=DigisacClientSchema)
async def create_digisac_client(
    request: CreateDigisacClientSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_digisac_client_service(company_id, request, db)


@router.patch("/{digisac_client_id}", response_model=DigisacClientSchema)
async def update_digisac_client(
    digisac_client_id: int,
    request: UpdateDigisacClientSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_digisac_client_service(
        digisac_client_id, request, company_id, db
    )


@router.get("/{digisac_client_id}/services")
async def list_digisac_services(
    digisac_client_id: int,
    page: int = 1,
    service_name: str | None = None,
    service_id: str | None = None,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await list_services(
        digisac_client_id, company_id, page, service_name, service_id, db
    )


@router.get("/{digisac_client_id}/users")
async def list_digisac_users(
    digisac_client_id: int,
    page: int = 1,
    user_name: str = None,
    user_id: str = None,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await list_users(digisac_client_id, company_id, page, user_name, user_id, db)


@router.get("/{digisac_client_id}/departments")
async def list_digisac_departments(
    digisac_client_id: int,
    page: int = 1,
    department_name: str = None,
    department_id: str = None,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await list_departments(
        digisac_client_id, company_id, page, department_name, department_id, db
    )


@router.post("/{digisac_client_id}/departments", response_model=DepartmentSchema)
async def create_department(
    digisac_client_id: int,
    request: CreateDepartmentSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await create_department_service(digisac_client_id, request, company_id, db)


@router.patch(
    "/{digisac_client_id}/departments/{department_id}",
    response_model=DepartmentSchema,
)
async def update_department(
    digisac_client_id: int,
    department_id: int,
    request: UpdateDepartmentSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_department_service(
        digisac_client_id, department_id, request, company_id, db
    )


@router.delete("/{digisac_client_id}/departments/{department_id}")
async def delete_department(
    digisac_client_id: int,
    department_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_department_service(
        digisac_client_id, department_id, company_id, db
    )
