from typing import Annotated

from langchain.tools import InjectedToolArg, ToolRuntime, tool

from app.assistant_functions.assistant_function import register_tool
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Company
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client
from app.utils.model_utils import get_resource_from_db
from app.assistant_functions.runtime_context import RuntimeContext


@register_tool
@tool("reschedule_appointment")
async def reschedule_appointment(
    calendar_address: str,
    original_appointment_title: str,
    original_appointment_start_datetime: str,
    new_datetime: str,
    runtime: Annotated[ToolRuntime[RuntimeContext], InjectedToolArg],
) -> bool:
    """Reschedule an appointment to a new date and time."""
    assistant_id = runtime.context["assistant_id"]
    status = False

    with get_db_session_with_context() as db:
        assistant = get_resource_from_db(Assistant, assistant_id, db)
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=reschedule_appointment.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=reschedule_appointment.__name__,
            )

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(
                detail="Could not create the agenda client",
                function_name=reschedule_appointment.__name__,
            )

        status = await agenda_client.reschedule_event(
            calendar_address,
            original_appointment_start_datetime,
            original_appointment_title,
            new_datetime,
        )

    return status
