from datetime import datetime
import pytz

from openai.types.beta import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import retornar_sessao
from app.db.models import Assistant


def get_current_datetime_doc():
    return FunctionToolParam(
        function={
            "name": "get_current_datetime",
            "description": "A function to extract current date and time",
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


@register_function(get_current_datetime_doc())
def get_current_datetime(assistant_id: str, thread_id: str, **kwargs):
    timezone = "UTC"

    with retornar_sessao() as db:
        assistant_db = (
            db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
        )
        company = assistant_db.company
        timezone = company.timezone

    tz = pytz.timezone(timezone)
    now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")

    return {"current_datetime": now}
