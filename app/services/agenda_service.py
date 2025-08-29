from datetime import datetime, timedelta
import json
from sqlalchemy.orm import Session

from app.db.new_models import Assistant, Company, Contact, OutlookClient, GoogleCalendarClient
from app.services import RespostaConfirmacao
from app.utils.agenda_client import AgendaClient, EventoTituloAgenda, Schedule
from app.utils.google_calendar import GoogleCalendar
from app.utils.outlook import Outlook
from app.utils.assistants_client import AssistantsClient


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


# TODO: make this function better, and add typing
async def get_original_event_data(
        assistant: AssistantsClient,
        contact: Contact
):
    message = assistant.get_specific_message_from_thread(contact.current_thread_id, 0, "asc", 1)
    if message:
        mensagem_dict = json.loads(message)
        data = mensagem_dict.get("dados", {})
        if data:
            original_event_data = EventoTituloAgenda(
                endereco_agenda=data.get("email_agenda", ""),
                titulo=data.get("titulo", ""),
                start_datetime=data.get("data_hora_inicio", "")
            )
            return original_event_data
    return None


# TODO: check if this function is still needed or if it can be replaced by an assistant action
async def extract_event_data(
        agenda: str,
        evento: dict,
        data_atual: str,
        empresa: Company,
        db: Session
):
    instrucao = {
        "acao": "extrair_dados_evento",
        "dados": {
            "email_agenda": agenda,
            "titulo": evento.get("subject", ""),
            "local": evento.get("location", ""),
            "data_hora_inicio": evento.get("start").get("date_time"),
            "data_hora_fim": evento.get("end").get("date_time"),
            "data_hora_atual": data_atual
        }
    }

    assistente_db = db.query(Assistant).filter_by(proposito="agendar", id_empresa=empresa.id).first()

    try:
        if assistente_db is not None:
            assistente = AssistantsClient(assistant_name=assistente_db.nome, openai_assistant_id=assistente_db.assistantId, openai_api_key=empresa.openai_api_key)
            assistente.add_message(message=json.dumps(instrucao))
            resposta, thread_id = assistente.create_or_run_thread()
            resposta_obj = RespostaConfirmacao.from_dict(json.loads(resposta))
            return resposta_obj, thread_id
    except Exception as e:
        print(e)
    return {}, None
