from typing import Annotated

from langchain.tools import InjectedToolArg, ToolRuntime, tool

from app.assistant_functions.assistant_function import register_tool
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Employee
from app.utils.model_utils import get_resource_from_db
from app.assistant_functions.runtime_context import RuntimeContext


@register_tool
@tool("get_employees")
def get_employees(
    runtime: Annotated[ToolRuntime[RuntimeContext], InjectedToolArg],
) -> dict:
    """Return the company's employees."""
    assistant_id = runtime.context["assistant_id"]
    with get_db_session_with_context() as db:
        assistant = get_resource_from_db(Assistant, assistant_id, db)
        if assistant:
            company = assistant.company
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
