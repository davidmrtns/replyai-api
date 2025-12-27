from sqlalchemy.orm import Session

from app.db.models import Company, Employee, User
from app.exceptions.exceptions import ResourceNotFoundException


async def get_employee_from_db(employee_id: int, logged_in_user: User, db: Session):
    query = db.query(Company).join(Employee).filter_by(id=employee_id)
    if logged_in_user.company_id:
        query = query.filter_by(company_id=logged_in_user.company_id)

    employee = query.first()

    if not employee:
        raise ResourceNotFoundException(
            resource_type="Employee",
            resource_id=employee_id,
            detail="Employee not found for the specified company and ID.",
            user_friendly_detail="Employee not found.",
            http_status_code=404,
        )
    return employee
