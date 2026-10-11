from typing import Annotated

from langchain.tools import InjectedToolArg, ToolRuntime, tool

from app.assistant_functions.assistant_function import register_tool
from app.db.database import get_db_session_with_context
from app.db.models import Assistant, Company, Agenda, Contact
from app.exceptions.exceptions import FailedFunctionRunException
from app.utils.create_agenda_client import create_agenda_client
from app.utils.model_utils import get_resource_from_db
from app.assistant_functions.runtime_context import RuntimeContext


@register_tool
@tool("add_appointment_to_calendar")
async def add_appointment_to_calendar(
    calendar_code: str,
    date: str,
    title: str,
    description: str,
    localization: str,
    runtime: Annotated[ToolRuntime[RuntimeContext], InjectedToolArg],
) -> bool:
    """Add an appointment to a calendar on a given date."""
    assistant_id = runtime.context["assistant_id"]
    thread_id = runtime.context["thread_id"]
    status = False

    with get_db_session_with_context() as db:
        assistant = get_resource_from_db(Assistant, assistant_id, db)
        if not assistant:
            raise FailedFunctionRunException(
                detail="Assistant not found in the database",
                function_name=add_appointment_to_calendar.__name__,
            )

        company: Company = assistant.company
        if not company:
            raise FailedFunctionRunException(
                detail="Company not found in the database",
                function_name=add_appointment_to_calendar.__name__,
            )

        agenda = (
            db.query(Agenda)
            .filter_by(atalho=calendar_code, id_empresa=company.id)
            .first()
        )
        if not agenda:
            raise FailedFunctionRunException(
                detail="Agenda not found in the database",
                function_name=add_appointment_to_calendar.__name__,
            )

        agenda_client = create_agenda_client(company, db)
        if agenda_client is None:
            raise FailedFunctionRunException(
                detail="Could not create the agenda client",
                function_name=add_appointment_to_calendar.__name__,
            )

        contact = (
            db.query(Contact)
            .filter_by(current_thread_id=thread_id, company_id=company.id)
            .first()
        )

        if contact:
            subject = f"{title} - {contact.phone_number}"
        else:
            subject = title

        status = await agenda_client.add_event(
            agenda_address=agenda.address,
            data=date,
            subject=subject,
            description=description,
            localization=localization,
        )

    return status
