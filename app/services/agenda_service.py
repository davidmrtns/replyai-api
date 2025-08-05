from sqlalchemy.orm import Session

from app.db.new_models import Company, OutlookClient, GoogleCalendarClient
from app.utils.agenda_client import AgendaClient
from app.utils.google_calendar import GoogleCalendar
from app.utils.outlook import Outlook


def create_agenda_client(company: Company, db: Session) -> AgendaClient | None:
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
