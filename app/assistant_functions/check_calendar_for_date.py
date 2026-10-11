from typing import Annotated

from langchain.tools import InjectedToolArg, ToolRuntime, tool

from app.assistant_functions.assistant_function import register_tool
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Company, Agenda
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client
from app.utils.model_utils import get_resource_from_db
from app.assistant_functions.runtime_context import RuntimeContext


@register_tool
@tool("check_calendar_for_date")
async def check_calendar_for_date(
    calendar_code: str,
    suggestion_date: str,
    runtime: Annotated[ToolRuntime[RuntimeContext], InjectedToolArg],
) -> dict:
    """Get the availability of a calendar on a given date."""
    assistant_id = runtime.context["assistant_id"]
    date_info = {"status": "unavaliable", "schedule": []}

    with get_db_session_with_context() as db:
        assistant = get_resource_from_db(Assistant, assistant_id, db)
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=check_calendar_for_date.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=check_calendar_for_date.__name__,
            )

        agenda = (
            db.query(Agenda)
            .filter_by(atalho=calendar_code, id_empresa=company.id)
            .first()
        )
        if not agenda:
            raise FailedFunctionRunException(
                detail="Agenda not found in the database",
                function_name=check_calendar_for_date.__name__,
            )

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(
                detail="Could not create the agenda client",
                function_name=check_calendar_for_date.__name__,
            )

        schedules = await agenda_client.get_schedules(
            agendas=[agenda.endereco], date=suggestion_date
        )
        if len(schedules) < 1:
            return date_info

        first_agenda_schedule = schedules[0]
        if first_agenda_schedule is None:
            return date_info

        if set(first_agenda_schedule.availability_view) == {"2"}:
            date_info["status"] = "closed_all_day"
        else:
            date_info["status"] = "available"
            date_info["schedule"] = first_agenda_schedule.to_string_list(company)

    return date_info
