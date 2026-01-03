import os
from datetime import datetime, timedelta
from typing import List, Literal

import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from app.utils.api_key_encryption import decrypt_api_key

from ..agenda_client import AgendaClient, Schedule
from .google_calendar_client_helpers import CredentialData
from app.db.models import GoogleCalendarClient as GoogleCalendarClientDB


class GoogleCalendarClient(AgendaClient):
    def __init__(
        self,
        credential_data: CredentialData,
        starting_time: str,
        ending_time: str,
        event_duration: int,
        timezone: str,
        client_db: GoogleCalendarClientDB,
        db: Session,
    ):
        decrypted_access_token = decrypt_api_key(credential_data.access_token)
        decrypted_refresh_token = decrypt_api_key(credential_data.refresh_token)

        credentials = Credentials.from_authorized_user_info(
            info={
                "access_token": decrypted_access_token,
                "refresh_token": decrypted_refresh_token,
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/calendar"],
            }
        )

        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

            if credentials.token != access_token:
                access_token = credentials.token
                refresh_token = (
                    credentials.refresh_token
                    if credentials.refresh_token
                    else refresh_token
                )

                client_db.refresh_token = (refresh_token,)
                client_db.access_token = (access_token,)
                db.commit()

        self.service = build("calendar", "v3", credentials=credentials)
        self.starting_time = starting_time
        self.ending_time = ending_time
        self.event_duration = event_duration
        self.timezone = pytz.timezone(timezone)

    async def get_schedules(self, agendas: List[str], date: str) -> List[Schedule]:
        responses = []

        for agenda in agendas:
            response = (
                self.service.events()
                .list(
                    calendarId=agenda,
                    timeMin=f"{date}T{self.starting_time}Z",
                    timeMax=f"{date}T{self.ending_time}Z",
                )
                .execute()
            )
            responses.append(response)

        config = {
            "event_duration": self.event_duration,
            "agenda_start_time": self.starting_time,
            "agenda_end_time": self.ending_time,
            "timezone": self.timezone,
            "checked_date": date,
        }

        return [Schedule.from_dict(data=item, config=config) for item in responses]

    async def add_event(
        self,
        agenda_address: str,
        date: str,
        subject: str,
        description: str | None = None,
        location: str | None = None,
    ) -> bool:
        initial_datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S").astimezone(
            self.timezone
        )
        end_datetime = initial_datetime + timedelta(minutes=self.event_duration)

        event = {
            "summary": subject,
            "start": {
                "dateTime": initial_datetime.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "timeZone": str(self.timezone),
            },
            "end": {
                "dateTime": end_datetime.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "timeZone": str(self.timezone),
            },
        }

        if description:
            event["description"] = description

        if location:
            event["location"] = location

        response = (
            self.service.events()
            .insert(calendarId=agenda_address, body=event)
            .execute()
        )
        return True if response else False

    async def confirm_event(
        self, agenda_address: str, event_start_datetime: str, event_subject: str
    ) -> bool:
        try:
            event = await self._select_specific_event(
                agenda_address, event_start_datetime, event_subject
            )

            if event:
                event["summary"] = (
                    f"CONFIRMADO - {event['summary']}"  # TODO: localize string
                )
                self.service.events().update(
                    calendarId=agenda_address, eventId=event["id"], body=event
                ).execute()
                return True
        except Exception as e:
            # TODO: throw exception
            print(e)
        return False

    async def reschedule_event(
        self,
        agenda_address: str,
        event_start_datetime: str,
        event_subject: str,
        new_datetime: str,
    ) -> bool:
        try:
            event = await self._select_specific_event(
                agenda_address, event_start_datetime, event_subject
            )

            if event:
                intial_datetime = datetime.strptime(
                    new_datetime, "%Y-%m-%dT%H:%M:%S"
                ).astimezone(self.timezone)
                end_datetime = intial_datetime + timedelta(minutes=self.event_duration)

                event["summary"] = (
                    f"REAGENDADO - {event['summary']}"  # TODO: localize string
                )
                event["start"] = {
                    "dateTime": intial_datetime.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "timeZone": str(self.timezone),
                }
                event["end"] = {
                    "dateTime": end_datetime.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "timeZone": str(self.timezone),
                }

                self.service.events().update(
                    calendarId=agenda_address, eventId=event["id"], body=event
                ).execute()
                return True
        except Exception as e:
            # TODO: throw exception
            print(e)
        return False

    async def cancel_event(
        self,
        agenda_address: str,
        event_start_datetime: str,
        event_subject: str,
        event_cancellation_type: Literal['keep"', "delete"],
    ) -> bool:
        try:
            event = await self._select_specific_event(
                agenda_address, event_start_datetime, event_subject
            )

            if event:
                if event_cancellation_type == "delete":
                    self.service.events().delete(
                        calendarId=agenda_address, eventId=event["id"]
                    ).execute()
                elif event_cancellation_type == 'keep"':
                    event["summary"] = (
                        f"CANCELADO - {event['summary']}"  # TODO: localize string
                    )
                    self.service.events().update(
                        calendarId=agenda_address, eventId=event["id"], body=event
                    ).execute()
                return True
        except Exception as e:
            # TODO: throw exception
            print(e)
        return False

    async def _select_specific_event(
        self, agenda_address: str, event_start_datetime: str, event_subject: str
    ) -> dict | None:
        events = (
            self.service.events()
            .list(
                calendarId=agenda_address, q=event_subject, timeMin=event_start_datetime
            )
            .execute()
        )

        return (
            events.get("items")[0]
            if events.get("items") and len(events.get("items")) > 0
            else None
        )
