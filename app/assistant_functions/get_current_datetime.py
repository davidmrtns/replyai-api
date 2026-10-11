from datetime import datetime
from typing import Annotated

import pytz
from langchain.tools import InjectedToolArg, ToolRuntime, tool

from app.db.database import get_db_session_with_context
from app.db.models import Assistant
from app.utils.model_utils import get_resource_from_db
from app.assistant_functions.runtime_context import RuntimeContext


@tool("get_current_datetime")
def get_current_datetime(
    runtime: Annotated[ToolRuntime[RuntimeContext], InjectedToolArg],
) -> dict[str, str]:
    """Extract the current date and time for the assistant's company timezone."""
    timezone = "UTC"

    with get_db_session_with_context() as db:
        assistant = get_resource_from_db(Assistant, runtime.context["assistant_id"], db)
        company = assistant.company
        timezone = company.timezone

    tz = pytz.timezone(timezone)
    now = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S")

    return {"current_datetime": now}
