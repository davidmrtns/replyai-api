from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Literal
from msgraph.generated.models.schedule_information import ScheduleInformation

from app.db.models import Company


class DateTimeInfo:
    def __init__(self, date_time: str, time_zone: str):
        self.date_time = date_time
        self.time_zone = time_zone


class ScheduleItem:
    def __init__(
        self,
        start: DateTimeInfo,
        end: DateTimeInfo,
        location: str,
        is_private: bool,
        status: str,
        subject: str,
    ):
        self.start = start
        self.end = end
        self.location = location
        self.is_private = is_private
        self.status = status
        self.subject = subject


class Schedule:
    def __init__(
        self,
        availability_view: str,
        schedule_id: str,
        schedule_items: List[ScheduleItem],
    ):
        self.availability_view = availability_view
        self.schedule_id = schedule_id
        self.schedule_items = schedule_items

    @classmethod
    def from_object(cls, data: ScheduleInformation):
        schedule_items = [
            ScheduleItem(
                start=DateTimeInfo(
                    date_time=item.start.date_time,
                    time_zone=item.start.time_zone,
                ),
                end=DateTimeInfo(
                    date_time=item.end.date_time,
                    time_zone=item.end.time_zone,
                ),
                location=item.location,
                is_private=item.is_private,
                status=item.status,
                subject=item.subject,
            )
            for item in data.schedule_items
        ]

        return cls(
            availability_view=data.availability_view,
            schedule_id=data.schedule_id,
            schedule_items=schedule_items,
        )

    @classmethod
    def from_dict(cls, data: dict, config: dict):
        events = [
            ScheduleItem(
                start=DateTimeInfo(
                    date_time=item.get("start", {}).get("dateTime", ""),
                    time_zone=item.get("start", {}).get("timeZone", ""),
                ),
                end=DateTimeInfo(
                    date_time=item.get("end", {}).get("dateTime", ""),
                    time_zone=item.get("end", {}).get("timeZone", ""),
                ),
                location=item.get("location", ""),
                is_private=False,
                status=item.get("status", ""),
                subject=item.get("summary", ""),
            )
            for item in data.get("items", [])
        ]

        availability_view = cls.generate_availability_view(
            events=events,
            interval=config.get("event_duration"),
            start_time=config.get("agenda_start_time"),
            end_time=config.get("agenda_end_time"),
            date=config.get("checked_date"),
            timezone=config.get("timezone"),
        )

        return cls(
            availability_view=availability_view,
            schedule_id=data.get("summary", ""),
            schedule_items=events,
        )

    def to_string_list(self, company: Company) -> list[str]:
        start = datetime.strptime(company.agenda_starting_time, "%H:%M:%S")
        end = datetime.strptime(company.agenda_ending_time, "%H:%M:%S")
        duration = timedelta(minutes=company.appointment_duration_in_minutes)

        slots = []
        current = start

        for i, availability in enumerate(self.availability_view):
            if current >= end:
                break

            if availability == "0":  # available time slot
                slots.append(current.strftime("%H:%M"))

            current += duration
        return slots

    @staticmethod
    def generate_availability_view(
        events: List[ScheduleItem],
        interval: int,
        start_time: str,
        end_time: str,
        date: str,
        timezone,
    ):
        start_time_dt = timezone.localize(
            datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
        )
        end_time_dt = timezone.localize(
            datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
        )

        total_minutes = int((end_time_dt - start_time_dt).total_seconds() // 60)
        total_blocks = total_minutes // interval
        blocks = ["0"] * total_blocks

        for event in events:
            event_start_time = datetime.fromisoformat(event.start.date_time)
            event_end_time = datetime.fromisoformat(event.end.date_time)

            offset = int((event_start_time - start_time_dt).total_seconds() // 60)
            initial_block_index = offset // interval

            event_duration = int(
                (event_end_time - event_start_time).total_seconds() // 60
            )

            for i in range(
                initial_block_index,
                initial_block_index + (event_duration // interval) + 1,
            ):
                if i < total_blocks:
                    blocks[i] = "2"

        return "".join(blocks)


class AgendaClient(ABC):
    @abstractmethod
    async def get_schedules(self, agendas: List[str], date: str) -> List[Schedule]:
        pass

    @abstractmethod
    async def add_event(
        self,
        agenda_address: str,
        date: str,
        subject: str,
        description: str | None = None,
        location: str | None = None,
    ) -> bool:
        pass

    @abstractmethod
    async def confirm_event(
        self, agenda_address: str, event_start_datetime: str, event_subject: str
    ) -> bool:
        pass

    @abstractmethod
    async def reschedule_event(
        self,
        agenda_address: str,
        event_start_datetime: str,
        event_subject: str,
        new_datetime: str,
    ) -> bool:
        pass

    @abstractmethod
    async def cancel_event(
        self,
        agenda_address: str,
        event_start_datetime: str,
        event_subject: str,
        event_cancellation_type: Literal['keep"', "delete"],
    ) -> bool:
        pass
