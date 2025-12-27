from fastapi import APIRouter
from fastapi.params import Depends
from requests import Session

from app.db.database import obter_sessao
from app.db.models import Employee, User
from .employee_helpers import get_employee_from_db
from app.routers.routers_helpers import require_auth, validate_company_id
from app.routers.user.user import get_logged_in_user
from app.schemas.employee_schema import (
    CreateEmployeeSchema,
    EmployeeSchema,
    UpdateEmployeeSchema,
)
from app.utils.apply_model_update import apply_model_update


router = APIRouter(dependencies=[Depends(require_auth)])


# TODO: maybe add a GET endpoint to list employees, or get one by ID


@router.post("/", response_model=EmployeeSchema)
async def create_employee(
    request: CreateEmployeeSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    validate_company_id(logged_in_user, request)

    employee = Employee(
        name=request.name,
        nickname=request.nickname,
        department_name=request.department_name,
        company_id=logged_in_user.company_id or request.company_id,
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


@router.patch("/{employee_id}", response_model=EmployeeSchema)
async def update_employee(
    employee_id: int,
    request: UpdateEmployeeSchema,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    employee = await get_employee_from_db(employee_id, logged_in_user, db)

    apply_model_update(employee, request)
    db.commit()
    return employee


@router.delete("/{employee_id}")
async def delete_employee(
    employee_id: int,
    logged_in_user: User = Depends(get_logged_in_user),
    db: Session = Depends(obter_sessao),
):
    employee = await get_employee_from_db(employee_id, logged_in_user, db)

    if employee:
        db.delete(employee)
        db.commit()
        return True
    return False
