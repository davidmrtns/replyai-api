from requests import Session

from app.db.models import (
    Company,
    GoogleCalendarClient as GoogleCalendarClientDB,
    OutlookClient as OutlookClientDB,
)
from app.clients.agenda_client import AgendaClient
from app.clients.google.google_calendar_client import GoogleCalendarClient
from app.clients.microsoft.outlook_client import OutlookClient
from app.utils.api_key_encryption import decrypt_api_key


def build_outlook_client(
    outlook_client_db: OutlookClientDB, db: Session
) -> OutlookClient:
    return OutlookClient(
        credential_data=(
            decrypt_api_key(outlook_client_db.access_token),
            decrypt_api_key(outlook_client_db.refresh_token),
            outlook_client_db.expires_in,
            outlook_client_db.expires_at,
        ),
        default_user_email=outlook_client_db.default_user,
        starting_time=outlook_client_db.company.agenda_starting_time.strftime(
            "%H:%M:%S"
        ),
        ending_time=outlook_client_db.company.agenda_ending_time.strftime("%H:%M:%S"),
        event_duration=outlook_client_db.company.appointment_duration_in_minutes,
        timezone=outlook_client_db.timezone,
        client_db=outlook_client_db,
        db=db,
    )


def build_google_calendar_client(
    googlecalendar_client_db: GoogleCalendarClientDB, db: Session
) -> GoogleCalendarClient:
    return GoogleCalendarClient(
        credential_data=(
            googlecalendar_client_db.access_token,
            googlecalendar_client_db.refresh_token,
        ),
        starting_time=googlecalendar_client_db.company.agenda_starting_time.strftime(
            "%H:%M:%S"
        ),
        ending_time=googlecalendar_client_db.company.agenda_ending_time.strftime(
            "%H:%M:%S"
        ),
        event_duration=googlecalendar_client_db.company.appointment_duration_in_minutes,
        timezone=googlecalendar_client_db.timezone,
        client_db=googlecalendar_client_db,
        db=db,
    )


def create_agenda_client(company: Company, db: Session) -> AgendaClient | None:
    if company.agenda_client_type == "outlook":
        outlook_client_db: OutlookClientDB = (
            db.query(OutlookClientDB).filter_by(company_id=company.id).first()
        )
        if outlook_client_db:
            return build_outlook_client(outlook_client_db, db)
    elif company.agenda_client_type == "google_calendar":
        googlecalendar_client_db: GoogleCalendarClientDB = (
            db.query(GoogleCalendarClientDB).filter_by(company_id=company.id).first()
        )
        if googlecalendar_client_db:
            return build_google_calendar_client(googlecalendar_client_db, db)
    return None
