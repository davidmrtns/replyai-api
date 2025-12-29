from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Department
from app.db.models import DigisacClient
from app.routers.integrations.digisac.digisac_helpers import (
    get_department_from_db,
    build_digisac_client,
)
from app.routers.routers_helpers import (
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
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


router = APIRouter()


@router.post("/", response_model=DigisacClientSchema)
async def create_digisac_client(
    request: CreateDigisacClientSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    digisac_client_db = db.query(DigisacClient).filter_by(company_id=company_id).first()
    if digisac_client_db:
        raise HTTPException(
            status_code=409,
            detail="This company already has a Digisac client registered",
        )

    digisac_client = DigisacClient(
        digisac_slug=request.digisac_slug,
        service_id=request.service_id,
        digisac_token=encrypt_api_key(request.digisac_token),
        digisac_default_user=request.digisac_default_user,
        company_id=company_id,
    )

    db.add(digisac_client)
    db.commit()
    db.refresh(digisac_client)
    return digisac_client


@router.patch("/{digisac_client_id}", response_model=DigisacClientSchema)
async def update_digisac_client(
    digisac_client_id: int,
    request: UpdateDigisacClientSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    update_data = request.model_dump(exclude_unset=True)

    if "digisac_token" in update_data:
        update_data["digisac_token"] = encrypt_api_key(update_data["digisac_token"])

    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )

    apply_model_update(digisac_client_db, update_data)
    db.commit()
    return digisac_client_db


@router.get("/{digisac_client_id}/services")
async def list_digisac_services(
    digisac_client_id: int,
    page: int = 1,
    service_name: str = None,
    service_id: str = None,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )
    digisac_client = build_digisac_client(digisac_client_db)

    response = digisac_client.list_services(page, service_name, service_id)
    return response


@router.get("/{digisac_client_id}/users")
async def list_digisac_users(
    digisac_client_id: int,
    page: int = 1,
    user_name: str = None,
    user_id: str = None,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )
    digisac_client = build_digisac_client(digisac_client_db)

    response = digisac_client.list_users(page, user_name, user_id)
    return response


@router.get("/{digisac_client_id}/departments")
async def list_digisac_departments(
    digisac_client_id: int,
    page: int = 1,
    department_name: str = None,
    department_id: str = None,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )
    digisac_client = build_digisac_client(digisac_client_db)

    response = digisac_client.list_departments(page, department_name, department_id)
    return response


@router.post("/{digisac_client_id}/departments", response_model=DepartmentSchema)
async def create_department(
    digisac_client_id: int,
    request: CreateDepartmentSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )

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
    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )
    department = get_department_from_db(digisac_client_db, department_id, db)

    apply_model_update(department, request)
    db.commit()
    return department


@router.delete("/{digisac_client_id}/departments/{department_id}")
async def delete_department(
    digisac_client_id: int,
    department_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    digisac_client_db = await get_resource_from_db(
        DigisacClient, digisac_client_id, db, company_id
    )
    department = get_department_from_db(digisac_client_db, department_id, db)

    db.delete(department)
    db.commit()
    return True
