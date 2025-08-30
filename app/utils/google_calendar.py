import os
from datetime import datetime, timedelta
from typing import Awaitable, List

import pytz
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from sqlalchemy.orm import Session

from app.db.new_models import GoogleCalendarClient
from app.utils.agenda_client import AgendaClient, Schedule, EventoTituloAgenda, EventoTituloAgendaDataNova


class GoogleCalendar(AgendaClient):
    def __init__(self, access_token: str, refresh_token: str, duracao_evento: int, hora_inicio_agenda: str, hora_final_agenda: str, timezone: str, client_db: GoogleCalendarClient, db: Session):
        creds = Credentials.from_authorized_user_info(
            info={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "token_uri": "https://oauth2.googleapis.com/token",
                "scopes": ["https://www.googleapis.com/auth/calendar"]
            }
        )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

            if creds.token != access_token:
                access_token = creds.token
                refresh_token = creds.refresh_token if creds.refresh_token else refresh_token

                client_db.refresh_token = refresh_token,
                client_db.access_token = access_token,
                db.commit()

        self.service = build("calendar", "v3", credentials=creds)
        self.hora_inicio_agenda = hora_inicio_agenda
        self.hora_final_agenda = hora_final_agenda
        self.timezone = pytz.timezone(timezone)
        self.duracao_evento = duracao_evento

    async def obter_horarios(self, agendas: list[str], data: str) -> Awaitable[List[Schedule]]:
        responses = []

        for agenda in agendas:
            response = self.service.events().list(
                calendarId=agenda,
                timeMin=f"{data}T{self.hora_inicio_agenda}Z",
                timeMax=f"{data}T{self.hora_final_agenda}Z"
            ).execute()
            responses.append(response)

        config = {
            "duracao_evento": self.duracao_evento,
            "hora_inicio_agenda": self.hora_inicio_agenda,
            "hora_final_agenda": self.hora_final_agenda,
            "timezone": self.timezone,
            "data_consulta": data
        }

        return [Schedule.from_dict(data=item, config=config) for item in responses]

    async def cadastrar_evento(self, agenda: str, data: str, titulo: str, descricao: str, localizacao: str):
        data = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S').astimezone(self.timezone)
        data_final = data + timedelta(minutes=self.duracao_evento)

        evento = {
            "summary": titulo,
            "start": {
                "dateTime": data.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "timeZone": str(self.timezone)
            },
            "end": {
                "dateTime": data_final.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "timeZone": str(self.timezone)
            }
        }

        if descricao:
            evento["description"] = descricao

        if localizacao:
            evento["location"] = localizacao

        evento_cadastrado = self.service.events().insert(calendarId=agenda, body=evento).execute()
        return evento_cadastrado

    async def confirmar_evento(self, dados: EventoTituloAgenda):
        try:
            eventos = self.service.events().list(
                calendarId=dados.endereco_agenda,
                q=dados.titulo,
                timeMin=dados.start_datetime
            ).execute()

            evento_obj = eventos.get("items")[0] if eventos.get("items") else None

            if evento_obj:
                evento_obj["summary"] = f"CONFIRMADO - {evento_obj['summary']}"
                self.service.events().update(
                    calendarId=dados.endereco_agenda,
                    eventId=evento_obj["id"],
                    body=evento_obj
                ).execute()
                return True
        except Exception as e:
            print(e)
        return False

    async def reagendar_evento(self, dados: EventoTituloAgendaDataNova):
        try:
            eventos = self.service.events().list(
                calendarId=dados.endereco_agenda,
                q=dados.titulo,
                timeMin=dados.start_datetime
            ).execute()

            evento_obj = eventos.get("items")[0] if eventos.get("items") else None

            if evento_obj:
                data = datetime.strptime(dados.data_nova, '%Y-%m-%dT%H:%M:%S').astimezone(self.timezone)
                data_final = data + timedelta(minutes=self.duracao_evento)

                evento_obj["summary"] = f"REAGENDADO - {evento_obj['summary']}"
                evento_obj["start"] = {
                    "dateTime": data.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "timeZone": str(self.timezone)
                }
                evento_obj["end"] = {
                    "dateTime": data_final.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "timeZone": str(self.timezone)
                }

                self.service.events().update(
                    calendarId=dados.endereco_agenda,
                    eventId=evento_obj["id"],
                    body=evento_obj
                ).execute()
                return True
        except Exception as e:
            print(e)
        return False

    async def cancelar_evento(self, dados: EventoTituloAgenda, tipo_cancelamento: str):
        try:
            eventos = self.service.events().list(
                calendarId=dados.endereco_agenda,
                q=dados.titulo,
                timeMin=dados.start_datetime
            ).execute()

            evento_obj = eventos.get("items")[0] if eventos.get("items") else None

            if evento_obj:
                if tipo_cancelamento == "excluir":
                    self.service.events().delete(
                        calendarId=dados.endereco_agenda,
                        eventId=evento_obj["id"]
                    ).execute()
                elif tipo_cancelamento == "manter":
                    evento_obj["summary"] = f"CANCELADO - {evento_obj['summary']}"
                    self.service.events().update(
                        calendarId=dados.endereco_agenda,
                        eventId=evento_obj["id"],
                        body=evento_obj
                    ).execute()
                return True
        except Exception as e:
            print(e)
        return False
