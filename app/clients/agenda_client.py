from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Literal
from msgraph.generated.models.schedule_information import ScheduleInformation
import pytz

from app.db.models import Company


class Schedule:
    def __init__(self, availability_view: str, schedule_id: str, schedule_items: list):
        self.availability_view = availability_view
        self.schedule_id = schedule_id
        self.schedule_items = schedule_items

    @classmethod
    def from_object(cls, data: ScheduleInformation):
        schedule_items = [
            {
                "start": {
                    "date_time": item.start.date_time,
                    "time_zone": item.start.time_zone,
                },
                "end": {
                    "date_time": item.end.date_time,
                    "time_zone": item.end.time_zone,
                },
                "location": item.location,
                "is_private": item.is_private,
                "status": item.status,
                "subject": item.subject,
            }
            for item in data.schedule_items
        ]

        return cls(
            availability_view=data.availability_view,
            schedule_id=data.schedule_id,
            schedule_items=schedule_items,
        )

    @classmethod
    def from_dict(cls, data: dict, config: dict):
        eventos = [
            {
                "start": {
                    "date_time": item.get("start", {}).get("dateTime", ""),
                    "time_zone": item.get("start", {}).get("timeZone", ""),
                },
                "end": {
                    "date_time": item.get("end", {}).get("dateTime", ""),
                    "time_zone": item.get("end", {}).get("timeZone", ""),
                },
                "location": item.get("location", ""),
                "is_private": False,
                "status": item.get("status", ""),
                "subject": item.get("summary", ""),
            }
            for item in data.get("items", [])
        ]

        availability_view = cls.gerar_availability_view(
            eventos=eventos,
            intervalo=config.get("duracao_evento"),
            hora_inicio=config.get("hora_inicio_agenda"),
            hora_final=config.get("hora_final_agenda"),
            timezone=config.get("timezone"),
            data=config.get("data_consulta"),
        )

        return cls(
            availability_view=availability_view,
            schedule_id=data.get("summary", ""),
            schedule_items=eventos,
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
    def gerar_availability_view(
        eventos: List[dict],
        intervalo: int,
        hora_inicio: str,
        hora_final: str,
        data: str,
        timezone: pytz.timezone,
    ):
        hora_inicio_dt = timezone.localize(
            datetime.strptime(f"{data} {hora_inicio}", "%Y-%m-%d %H:%M:%S")
        )
        hora_final_dt = timezone.localize(
            datetime.strptime(f"{data} {hora_final}", "%Y-%m-%d %H:%M:%S")
        )

        total_minutos = int((hora_final_dt - hora_inicio_dt).total_seconds() // 60)
        total_blocos = total_minutos // intervalo
        blocks = ["0"] * total_blocos

        for evento in eventos:
            inicio_evento = datetime.fromisoformat(evento["start"]["date_time"])
            fim_evento = datetime.fromisoformat(evento["end"]["date_time"])

            offset = int((inicio_evento - hora_inicio_dt).total_seconds() // 60)
            index_inicial_bloco = offset // intervalo

            duracao_evento = int((fim_evento - inicio_evento).total_seconds() // 60)

            for i in range(
                index_inicial_bloco,
                index_inicial_bloco + (duracao_evento // intervalo) + 1,
            ):
                if i < total_blocos:
                    blocks[i] = "2"

        return "".join(blocks)


class AgendaClient(ABC):
    @abstractmethod
    def get_schedules(self, agendas: List[str], date: str) -> List[Schedule]:
        pass

    @abstractmethod
    def add_event(
        self,
        agenda_address: str,
        date: str,
        subject: str,
        description: str | None = None,
        location: str | None = None,
    ) -> bool:
        pass

    @abstractmethod
    def confirm_event(
        agenda_address: str, event_start_datetime: str, event_subject: str
    ) -> bool:
        pass

    @abstractmethod
    def reschedule_event(
        agenda_address: str,
        event_start_datetime: str,
        event_subject: str,
        new_datetime: str,
    ) -> bool:
        pass

    @abstractmethod
    def cancel_event(
        agenda_address: str,
        event_start_datetime: str,
        event_subject: str,
        event_cancellation_type: Literal['keep"', "delete"],
    ) -> bool:
        pass
