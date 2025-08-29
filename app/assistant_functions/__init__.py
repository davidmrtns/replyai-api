from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models import Agenda
from app.db.new_models import Assistant, Company, GoogleCalendarClient, OutlookClient
from app.utils.agenda_client import AgendaClient
from app.utils.google_calendar import GoogleCalendar
from app.utils.outlook import Outlook


# TODO: move to a utils file, since it's being used between services, assistant functions and clients
def _create_agenda_client(company: Company, db: Session) -> AgendaClient | None:
    if company.agenda_client_type == "outlook":
        outlook_client = db.query(OutlookClient).filter_by(company_id=company.id).first()
        if outlook_client:
            return Outlook(
                access_token=outlook_client.access_token,
                refresh_token=outlook_client.refresh_token,
                expires_in=outlook_client.expires_in,
                expires_at=outlook_client.expires_at,
                usuarioPadrao=outlook_client.default_user,
                duracaoEvento=company.appointment_duration_in_minutes,
                horaInicioAgenda=company.agenda_starting_time.strftime("%H:%M:%S"),
                horaFinalAgenda=company.agenda_ending_time.strftime("%H:%M:%S"),
                timeZone=outlook_client.timezone,
                client_db=outlook_client,
                db=db
            )
    else:
        googlecalendar_client = db.query(GoogleCalendarClient).filter_by(company_id=company.id).first()
        if googlecalendar_client:
            return GoogleCalendar(
                access_token=googlecalendar_client.access_token,
                refresh_token=googlecalendar_client.refresh_token,
                duracao_evento=company.appointment_duration_in_minutes,
                hora_inicio_agenda=company.agenda_starting_time.strftime("%H:%M:%S"),
                hora_final_agenda=company.agenda_ending_time.strftime("%H:%M:%S"),
                timezone=googlecalendar_client.timezone,
                client_db=googlecalendar_client,
                db=db
            )
    return None


# TODO: call it a better name and add typing
async def _get_variables(
        assistant_id: str,
        agenda_code: str | None,
        db: Session,
):
    assistant = db.query(Assistant).filter_by(openai_assistant_id=assistant_id).first()
    
    if assistant is None:
        return None

    company = assistant.company

    if agenda_code is not None:
        agenda = db.query(Agenda).filter_by(atalho=agenda_code, id_empresa=company.id).first()
        if agenda is None:
            return None
    else:
        agenda = None
    
    agenda_client = _create_agenda_client(company, db)
    if agenda_client is None:
        return None
    
    return company, assistant, agenda_client, agenda


# TODO: maybe move to agenda client class
def _schedule_to_list(
        schedule,
        company: Company
) -> list:
    start = datetime.strptime(company.agenda_starting_time, "%H:%M:%S")
    end = datetime.strptime(company.agenda_ending_time, "%H:%M:%S")
    duration = timedelta(minutes=company.appointment_duration_in_minutes)

    slots = []
    current = start

    for i, availability in enumerate(schedule.availability_view):
        if current >= end:
            break

        if availability == "0": # available time slot
            slots.append(current.strftime("%H:%M"))

        current += duration

    return slots


from app.assistant_functions.add_event_to_agenda import add_event_to_agenda
from app.assistant_functions.cancel_or_confirm_event import cancel_or_confirm_event
from app.assistant_functions.check_agenda_for_date import check_agenda_for_date
from app.assistant_functions.get_current_datetime import get_current_datetime
from app.assistant_functions.get_employees import get_employees
from app.assistant_functions.reschedule_event import reschedule_event
