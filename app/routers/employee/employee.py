from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import obter_sessao
from app.db.models import Employee
from app.utils.model_utils import get_resource_from_db, apply_model_update
from app.routers.routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.employee_schema import (
    CreateEmployeeSchema,
    EmployeeSchema,
    UpdateEmployeeSchema,
)


router = APIRouter()


# TODO: maybe add a GET endpoint to list employees, or get one by ID


@router.post("/", response_model=EmployeeSchema)
async def create_employee(
    request: CreateEmployeeSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(obter_sessao),
):
    employee = Employee(
        name=request.name,
        nickname=request.nickname,
        department_name=request.department_name,
        company_id=company_id,
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


@router.patch("/{employee_id}", response_model=EmployeeSchema)
async def update_employee(
    employee_id: int,
    request: UpdateEmployeeSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    employee = await get_resource_from_db(Employee, employee_id, db, company_id)

    apply_model_update(employee, request)
    db.commit()
    return employee


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    employee = await get_resource_from_db(Employee, employee_id, db, company_id)

    if employee:
        db.delete(employee)
        db.commit()
        return True
    return False
