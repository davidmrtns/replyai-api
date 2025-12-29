from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Employee


def get_employees_doc():
    return FunctionToolParam(
        function={
            "name": "get_employees",
            "description": "A function to return a list of employees",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
                "required": [],
            },
        },
        type="function",
    )


@register_function(get_employees_doc())
def get_employees(assistant_id: str, thread_id: str, **kwargs):
    with get_db_session_with_context() as db:
        assistant_db = (
            db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        )
        if assistant_db:
            company = assistant_db.company
            employees = db.query(Employee).filter_by(company_id=company.id).all()
            data = [
                {
                    "name": employee.name,
                    "nickname": employee.nickname,
                    "department": employee.department_name,
                }
                for employee in employees
            ]

            return {"employees": data}
    return {"employees": ""}
