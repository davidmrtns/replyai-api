from sqlalchemy.orm import Session

from app.db.models import Employee
from app.schemas.employee_schema import CreateEmployeeSchema, UpdateEmployeeSchema
from app.utils.model_utils import apply_model_update, get_resource_from_db


async def create_employee(payload: CreateEmployeeSchema, company_id: int, db: Session):
    employee = Employee(
        name=payload.name,
        nickname=payload.nickname,
        department_name=payload.department_name,
        company_id=company_id,
    )

    db.add(employee)
    db.commit()
    db.refresh(employee)

    return employee


async def update_employee(
    employee_id: int, payload: UpdateEmployeeSchema, company_id: int | None, db: Session
):
    employee = await get_resource_from_db(Employee, employee_id, db, company_id)

    apply_model_update(employee, payload)
    db.commit()
    return employee


async def delete_employee(employee_id: int, company_id: int | None, db: Session):
    employee = await get_resource_from_db(Employee, employee_id, db, company_id)

    if employee:
        db.delete(employee)
        db.commit()
        return True
    return False
