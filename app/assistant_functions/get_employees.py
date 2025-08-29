from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.models import Colaborador
from app.db.new_models import Assistant


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
                "required": []
            }
        },
        type="function"
    )


@register_function(get_employees_doc())
def get_employees(assistant_id: str, **kwargs):
    with retornar_sessao() as db:
        assistant_db = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        if assistant_db:
            company = assistant_db.company
            employees = db.query(Colaborador).filter_by(id_empresa=company.id).all()
            data = [
                {"name": employee.nome, "nickname": employee.apelido, "department": employee.departamento}
                for employee in employees
            ]

            return {"employees": data}
    return {"employees": ""}
