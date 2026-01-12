from datetime import datetime
import pytz
from openai.types.responses import FunctionToolParam

from app.assistant_functions.assistant_function import register_function
from app.db.database import get_db_session_with_context
from app.db.models import Assistant
from app.utils.model_utils import get_resource_from_db


def get_current_datetime_doc():
    return FunctionToolParam(
        name="get_current_datetime",
        description="A function to extract current date and time",
        strict=True,
        parameters={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
            "required": [],
        },
        type="function",
    )


@register_function(get_current_datetime_doc())
async def get_current_datetime(assistant_id: str, thread_id: str, **kwargs):
    timezone = "UTC"

    with get_db_session_with_context() as db:
        assistant = await get_resource_from_db(Assistant, assistant_id, db)
        company = assistant.company
        timezone = company.timezone

    tz = pytz.timezone(timezone)
    now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")

    return {"current_datetime": now}
