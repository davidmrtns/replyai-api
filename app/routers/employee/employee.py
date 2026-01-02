from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import get_db_session
from app.routers.routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.employee_schema import (
    CreateEmployeeSchema,
    EmployeeSchema,
    UpdateEmployeeSchema,
)
from app.services.employee_service import (
    create_employee as create_employee_service,
    update_employee as update_employee_service,
    delete_employee as delete_employee_service,
)


router = APIRouter()


@router.post("/", response_model=EmployeeSchema)
async def create_employee(
    request: CreateEmployeeSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_employee_service(request, company_id, db)


@router.patch("/{employee_id}", response_model=EmployeeSchema)
async def update_employee(
    employee_id: int,
    request: UpdateEmployeeSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_employee_service(employee_id, request, company_id, db)


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_employee_service(employee_id, company_id, db)
