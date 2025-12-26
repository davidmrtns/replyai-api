from datetime import datetime, timedelta
from typing import List, Literal
from msgraph.graph_service_client import GraphServiceClient
from sqlalchemy.orm import Session
from kiota_abstractions.base_request_configuration import RequestConfiguration
from msgraph.generated.users.item.calendar.get_schedule.get_schedule_post_request_body import (
    GetSchedulePostRequestBody,
)
from msgraph.generated.models.date_time_time_zone import DateTimeTimeZone
from msgraph.generated.models.event import Event
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.location import Location
from msgraph.generated.users.item.events.events_request_builder import (
    EventsRequestBuilder,
)
from msgraph.generated.models.free_busy_status import FreeBusyStatus

from ..agenda_client import AgendaClient, Schedule
from .outlook_client_helpers import CredentialData, OutlookAccessTokenCredential
from app.db.new_models import OutlookClient as OutlookClientDB


class OutlookClient(AgendaClient):
    def __init__(
        self,
        credential_data: CredentialData,
        default_user_email: str,
        starting_time: str,
        ending_time: str,
        event_duration: int,
        timezone: str,
        client_db: OutlookClientDB,
        db: Session,
    ):
        credential = OutlookAccessTokenCredential(credential_data, client_db, db)
        scopes = ["https://graph.microsoft.com/.default"]

        self.graph_client = GraphServiceClient(credentials=credential, scopes=scopes)
        self.default_user_email = default_user_email
        self.starting_time = starting_time
        self.ending_time = ending_time
        self.event_duration = event_duration
        self.timezone = timezone
        pass

    async def get_schedules(self, agendas: List[str], date: str) -> List[Schedule]:
        try:
            request_config = RequestConfiguration()

            request_config.headers.try_add(
                "Prefer", f"outlook.timezone='{self.timezone}'"
            )

            request_body = GetSchedulePostRequestBody()
            request_body.schedules = agendas
            request_body.start_time = DateTimeTimeZone(
                date_time=f"{date}T{self.starting_time}", time_zone=self.timezone
            )
            request_body.end_time = DateTimeTimeZone(
                date_time=f"{date}T{self.ending_time}", time_zone=self.timezone
            )
            request_body.availability_view_interval = self.event_duration

            response = await self.graph_client.users.by_user_id(
                self.default_user_email
            ).calendar.get_schedule.post(
                request_configuration=request_config, body=request_body
            )

            return [Schedule.from_object(item) for item in response.value]
        except Exception as e:
            # TODO: throw exception
            print(e)

    async def add_event(
        self,
        agenda_address: str,
        date: str,
        subject: str,
        description: str | None = None,
        location: str | None = None,
    ) -> bool:
        try:
            end_datetime = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S") + timedelta(
                minutes=self.event_duration
            )

            request_body = Event()
            request_body.subject = subject
            request_body.start = DateTimeTimeZone(
                date_time=date, time_zone=self.timezone
            )
            request_body.end = DateTimeTimeZone(
                date_time=f"{end_datetime.strftime('%Y-%m-%dT%H:%M:%S')}",
                time_zone=self.timezone,
            )

            if description:
                request_body.body = ItemBody(
                    content_type=BodyType("HTML"), content=description
                )

            if location:
                request_body.location = Location(display_name=location)

            await self.graph_client.users.by_user_id(agenda_address).events.post(
                body=request_body
            )
            return True
        except Exception as e:
            # TODO: throw exception
            print(e)
            return False

    async def confirm_event(
        self, agenda_address: str, event_start_datetime: str, event_subject: str
    ) -> bool:
        try:
            event = await self._select_specific_event(
                agenda_address, event_start_datetime, event_subject
            )
            if not event:
                return False

            request_body = Event()
            request_body.subject = (
                f"CONFIRMADO - {event.subject}"  # TODO: localize string
            )

            await self.graph_client.users.by_user_id(agenda_address).events.by_event_id(
                event.id
            ).patch(body=request_body)
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
            if not event:
                return False

            end_datetime = datetime.strptime(
                new_datetime, "%Y-%m-%dT%H:%M:%S"
            ) + timedelta(minutes=self.event_duration)

            request_body = Event()
            request_body.subject = (
                f"REAGENDADO - {event.subject}"  # TODO: localize string
            )
            request_body.start = DateTimeTimeZone(
                date_time=f"{new_datetime}", time_zone=self.timezone
            )
            request_body.end = DateTimeTimeZone(
                date_time=f"{end_datetime.strftime('%Y-%m-%dT%H:%M:%S')}",
                time_zone=self.timezone,
            )

            await self.graph_client.users.by_user_id(agenda_address).events.by_event_id(
                event.id
            ).patch(body=request_body)
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
            if not event:
                return False

            if event_cancellation_type == "keep":
                await self.graph_client.users.by_user_id(
                    agenda_address
                ).events.by_event_id(event.id).delete()
            elif event_cancellation_type == "delete":
                request_body = Event()
                request_body.subject = (
                    f"CANCELADO - {event.subject}"  # TODO: localize string
                )
                request_body.show_as = FreeBusyStatus("free")
                await self.graph_client.users.by_user_id(
                    agenda_address
                ).events.by_event_id(event.id).patch(body=request_body)
            else:
                # TODO: raise custom exception
                return False

            return True
        except Exception as e:
            # TODO: throw exception
            print(e)
            return False

    async def get_timezones(self):
        try:
            timezones = await self.graph_client.me.outlook.supported_time_zones.get()
            return [
                {"alias": item.alias, "display_name": item.display_name}
                for item in timezones.value
            ]
        except Exception as e:
            # TODO: throw exception
            print(f"Error while fetching timezones: {e}")
            return False

    async def _select_specific_event(
        self, agenda_address: str, event_start_datetime: str, event_subject: str
    ) -> Event | None:
        query_params = EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
            select=["start", "end", "subject", "id", "location"],
            filter=f"start/datetime eq '{event_start_datetime}' and subject eq '{event_subject}'",
        )

        request_config = RequestConfiguration(query_parameters=query_params)

        request_config.headers.try_add("Prefer", f"outlook.timezone='{self.timezone}'")

        response = await self.graph_client.users.by_user_id(agenda_address).events.get(
            request_configuration=request_config
        )
        return response.value[0] if len(response.value) > 0 else None
