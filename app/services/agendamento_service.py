from datetime import datetime, timedelta
import pytz
import json
from sqlalchemy.orm import Session

from app.db.new_models import Contact, Assistant, Company
from app.db.new_models import GoogleCalendarClient, OutlookClient
from app.utils.agenda_client import AgendaClient, EventoTituloAgenda, EventoTituloAgendaDataNova
from app.utils.assistant import Assistant as AiAssistant, Instrucao, RespostaDataSugerida, RespostaAgendamento, RespostaConfirmacao
from app.utils.google_calendar import GoogleCalendar
from app.utils.outlook import Outlook


async def verificar_data_sugerida(
        agenda_client: AgendaClient,
        contato: Contact,
        endereco_agenda: str,
        empresa: Company,
        db: Session
):
    timezone = pytz.timezone(empresa.timezone)
    hoje = datetime.now(timezone)
    hoje_formatado = hoje.strftime("%d/%m/%Y, %A")
    amanha = hoje + timedelta(days=1)
    amanha_formatado = amanha.strftime("%d/%m/%Y, %A")
    numero_semana = hoje.strftime("%U")
    semana_par_impar = "PAR" if int(numero_semana) % 2 == 0 else "ÍMPAR"

    instrucao = Instrucao(
        acao="verificar_data_sugerida",
        dados={
            "hoje": hoje_formatado,
            "sugestao_inicial": amanha_formatado,
            "numero_semana": numero_semana,
            "semana_par_impar": semana_par_impar
        }
    )

    assistente_db = db.query(Assistant).filter_by(proposito="agendar", id_empresa=empresa.id).first()

    if assistente_db is not None:
        assistente = AiAssistant(nome=assistente_db.assistant_name, id=assistente_db.openai_assistant_id, api_key=empresa.openai_api_key)
        assistente.adicionar_mensagens(mensagens=[instrucao.__str__()], id_arquivos=[], thread_id=contato.current_thread) # TODO: get thread openai id

        resposta, _ = assistente.criar_rodar_thread(thread_id=contato.threadId)
        resposta = RespostaDataSugerida.from_dict(json.loads(resposta))

        if resposta.tag == "DATA VÁLIDA":
            agendas = await agenda_client.obter_horarios(agendas=[endereco_agenda], data=resposta.data_sugerida)
            if agendas:
                agenda_disponivel = agendas[0]
                if agenda_disponivel is not None:
                    if set(agenda_disponivel.availability_view) == {"2"}:
                        dados_agenda = {
                            "titulo": agenda_disponivel.schedule_items[0]["subject"] or "",
                            "disponibilidade": agenda_disponivel.availability_view or ""
                        }
                        instrucao.acao = "agenda_fechada"
                    else:
                        dados_agenda = {
                            "data_sugerida": resposta.data_sugerida,
                            "disponibilidade": agenda_disponivel.availability_view,
                            "horario_inicial": agenda_client.hora_inicio_agenda,
                            "horario_final": agenda_client.hora_final_agenda,
                            "intervalo_tempo": agenda_client.duracao_evento
                        }
                        instrucao.acao = "agenda_disponivel"
                    instrucao.dados = dados_agenda
                    assistente.adicionar_mensagens(mensagens=[instrucao.__str__()], id_arquivos=[], thread_id=contato.threadId)

                    resposta, _ = assistente.criar_rodar_thread(thread_id=contato.threadId)
                    resposta = RespostaDataSugerida.from_dict(json.loads(resposta))
                    return resposta.mensagem
        else:
            return resposta.mensagem
    return None


async def cadastrar_evento(
        agenda_client: AgendaClient,
        contato: Contact,
        endereco_agenda: str,
        empresa: Company,
        db: Session
):
    timezone = pytz.timezone(empresa.fuso_horario)
    hoje = datetime.now(timezone)
    hoje_formatado = hoje.strftime("%d/%m/%Y, %A")

    instrucao = Instrucao(
        acao="extrair_data_hora_escolhida",
        dados={
            "hoje": hoje_formatado
        }
    )

    assistente_db = db.query(Assistant).filter_by(proposito="agendar", id_empresa=empresa.id).first()

    if assistente_db is not None:
        assistente = AiAssistant(nome=assistente_db.nome, id=assistente_db.assistantId, api_key=empresa.openai_api_key)
        assistente.adicionar_mensagens(mensagens=[instrucao.__str__()], id_arquivos=[], thread_id=contato.threadId)

        resposta, _ = assistente.criar_rodar_thread(thread_id=contato.threadId)
        resposta = RespostaAgendamento.from_dict(json.loads(resposta))

        if resposta.tag == "DATA VÁLIDA":
            await agenda_client.cadastrar_evento(agenda=endereco_agenda, data=resposta.data_hora_agendamento,
                                                 titulo=resposta.titulo_evento, descricao=resposta.descricao,
                                                 localizacao=resposta.localizacao)
            return resposta.mensagem
        else:
            return resposta.mensagem
    return None


async def extrair_dados_evento(
        agenda: str,
        evento: dict,
        data_atual: str,
        empresa: Company,
        db: Session
):
    instrucao = Instrucao(
        acao="extrair_dados_evento",
        dados={
            "email_agenda": agenda,
            "titulo": evento.get("subject", ""),
            "local": evento.get("location", ""),
            "data_hora_inicio": evento.get("start").get("date_time"),
            "data_hora_fim": evento.get("end").get("date_time"),
            "data_hora_atual": data_atual
        }
    )

    assistente_db = db.query(Assistant).filter_by(proposito="agendar", id_empresa=empresa.id).first()

    try:
        if assistente_db is not None:
            assistente = AiAssistant(nome=assistente_db.nome, id=assistente_db.assistantId, api_key=empresa.openai_api_key)
            assistente.adicionar_mensagens(mensagens=[instrucao.__str__()], id_arquivos=[], thread_id=None)
            resposta, thread_id = assistente.criar_rodar_thread()
            resposta_obj = RespostaConfirmacao.from_dict(json.loads(resposta))
            return resposta_obj, thread_id
    except Exception as e:
        print(e)
    return {}, None


async def obter_titulo_agenda_evento(
        assistente: Assistant,
        contato: Contact,
        data_nova: str | None = None
):
    mensagem = assistente.obter_mensagem_thread(contato.threadId, 0, "asc", 1)
    if mensagem:
        mensagem_dict = json.loads(mensagem)
        dados_dict = mensagem_dict.get("dados", {})
        if dados_dict:
            if not data_nova:
                dados = EventoTituloAgenda(
                    endereco_agenda=dados_dict.get("email_agenda", ""),
                    titulo=dados_dict.get("titulo", ""),
                    start_datetime=dados_dict.get("data_hora_inicio", "")
                )
            else:
                dados = EventoTituloAgendaDataNova(
                    endereco_agenda=dados_dict.get("email_agenda", ""),
                    titulo=dados_dict.get("titulo", ""),
                    start_datetime=dados_dict.get("data_hora_inicio", ""),
                    data_nova=data_nova
                )
            return dados
    return None


async def obter_nova_data_reagendamento(
        thread_id: str,
        empresa: Company,
        db: Session
):
    instrucao = Instrucao(
        acao="obter_nova_data_reagendamento",
        dados=None
    )

    assistente_db = db.query(Assistant).filter_by(proposito="agendar", id_empresa=empresa.id).first()

    if assistente_db is not None:
        assistente = Assistant(nome=assistente_db.nome, id=assistente_db.assistantId, api_key=empresa.openai_api_key)
        assistente.adicionar_mensagens(mensagens=[instrucao.__str__()], id_arquivos=[], thread_id=thread_id)
        resposta, _ = assistente.criar_rodar_thread(thread_id)

        resposta_dict = json.loads(resposta)
        return resposta_dict.get("nova_data", "")
    return None


def criar_agenda_client(empresa: Company, db: Session):
    if empresa.agenda_client_type == "outlook":
        outlook_client_db = db.query(OutlookClient).filter_by(id_empresa=empresa.id).first()
        if outlook_client_db:
            return Outlook(
                access_token=outlook_client_db.access_token,
                refresh_token=outlook_client_db.refresh_token,
                expires_in=outlook_client_db.expires_in,
                expires_at=outlook_client_db.expires_at,
                usuarioPadrao=outlook_client_db.usuarioPadrao,
                duracaoEvento=empresa.duracao_evento,
                horaInicioAgenda=empresa.hora_inicio_agenda,
                horaFinalAgenda=empresa.hora_final_agenda,
                timeZone=outlook_client_db.timeZone,
                client_db=outlook_client_db,
                db=db
            )
    elif empresa.agenda_client_type == "google_calendar":
        googlecalendar_client_db = db.query(GoogleCalendarClient).filter_by(id_empresa=empresa.id).first()
        if googlecalendar_client_db:
            return GoogleCalendar(
                access_token=googlecalendar_client_db.access_token,
                refresh_token=googlecalendar_client_db.refresh_token,
                duracao_evento=empresa.duracao_evento,
                hora_inicio_agenda=empresa.hora_inicio_agenda,
                hora_final_agenda=empresa.hora_final_agenda,
                timezone=googlecalendar_client_db.timezone,
                client_db=googlecalendar_client_db,
                db=db
            )
