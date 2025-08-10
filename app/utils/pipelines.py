from sqlalchemy.orm import Session
from app.db.new_models import Contact
from app.services.agendamento_service import cadastrar_evento, obter_nova_data_reagendamento, obter_titulo_agenda_evento, verificar_data_sugerida
from app.services.company_service import get_agenda, get_assistant_from_company, get_department
from app.services.contato_service import atualizar_assistente_atual_contato, encerrar_contato, mudar_aguardando_humano, transferir_contato
from app.services.crm_service import mover_lead
from app.services.mensagem_service import enviar_mensagem
from app.services.thread_service import execute_thread
from app.types.types import CompanyData
from app.utils.assistant import Resposta, Assistant as AiAssistant
from app.utils.digisac import Digisac
from app.utils.logger import logger


async def _response_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media = response.mensagem, response.midia
        company, message_client, _, __ = company_data

        await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
        return True
    except Exception as e:
        logger.exception(f"Error in response pipeline: {e}")
    return False


async def _transfer_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media, department_code = response.mensagem, response.midia, response.departamento
        company, message_client, _, __ = company_data
        
        if isinstance(message_client, Digisac):
            department = await get_department(company, department_code, False, db)
            if department:
                await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
                await mudar_aguardando_humano(contact, True, db)
                await transferir_contato(message_client, contact, department)
            return True
    except Exception as e:
        logger.exception(f"Error in transfer pipeline: {e}")
    return False


async def _end_contact_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media = response.mensagem, response.midia
        company, message_client, _, __ = company_data

        await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
        await encerrar_contato(contact, message_client, db)
        return True
    except Exception as e:
        logger.exception(f"Error in end contact pipeline: {e}")
    return False


async def _migrate_assistant_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media, assistant_code = response.mensagem, response.midia, response.assistente
        company, message_client, _, __ = company_data

        await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
        assistant, assistant_id = await get_assistant_from_company(company, None, assistant_code, db)
        if assistant:
            new_response = await execute_thread(None, None, contact, assistant, db)
            await atualizar_assistente_atual_contato(contact, assistant_id, db)
            await enviar_mensagem(new_response.mensagem, is_audio, media, contact, company, message_client, assistant, db)
            return True
    except Exception as e:
        logger.exception(f"Error in migrate assistant pipeline: {e}")
    return False


async def _agenda_check_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        _, media, agenda_code = response.mensagem, response.midia, response.agenda
        company, message_client, agenda_client, __ = company_data

        if agenda_client is not None:
            agenda = await get_agenda(company, agenda_code, db)
            if agenda:
                new_response = await verificar_data_sugerida(agenda_client, contact, agenda.endereco, company, db)
                if new_response:
                    await enviar_mensagem(new_response, is_audio, media, contact, company, message_client, assistant, db)
                    return True
    except Exception as e:
        logger.exception(f"Error in agenda check pipeline: {e}")
    return False


async def _agenda_create_event_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        _, media, agenda_code, activity = response.mensagem, response.midia, response.agenda, response.atividade
        company, message_client, agenda_client, crm_client = company_data

        if agenda_client is not None:
            agenda = await get_agenda(company, agenda_code, db)
            if agenda:
                new_response = await cadastrar_evento(agenda_client, contact, agenda.endereco, company, db)
                await mover_lead(crm_client, contact, company, activity, db)
                if new_response:
                    await enviar_mensagem(new_response, is_audio, media, contact, company, message_client, assistant, db)
    except Exception as e:
        logger.exception(f"Error in agenda create event pipeline: {e}")
    return False


async def _agenda_reschedule_event_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media, activity = response.mensagem, response.midia, response.atividade
        company, message_client, agenda_client, crm_client = company_data

        if agenda_client is not None:
            new_date = await obter_nova_data_reagendamento(contact.current_thread.thread_id, company, db)
            if new_date:
                original_event_data = await obter_titulo_agenda_evento(assistant, contact, new_date)
                if original_event_data:
                    if await agenda_client.reagendar_evento(original_event_data):
                        await mover_lead(crm_client, contact, company, activity, db)
                        await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
                        await encerrar_contato(contact, message_client, db)
                        return True
    except Exception as e:
        logger.exception(f"Error in agenda reschedule event pipeline: {e}")
    return False


async def _agenda_cancel_event_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media, activity = response.mensagem, response.midia, response.atividade
        company, message_client, agenda_client, crm_client = company_data

        if agenda_client is not None:
            original_event_data = await obter_titulo_agenda_evento(assistant, contact)
            if original_event_data:
                if await agenda_client.cancelar_evento(original_event_data, company.event_cancellation_type):
                    await mover_lead(crm_client, contact, company, activity, db)
                    await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
                    await encerrar_contato(contact, message_client, db)
                    return True
    except Exception as e:
        logger.exception(f"Error in agenda cancel event pipeline: {e}")
    return False


async def _agenda_confirm_event_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AiAssistant,
        db: Session
) -> bool:
    try:
        message, media, activity = response.mensagem, response.midia, response.atividade
        company, message_client, agenda_client, crm_client = company_data

        if agenda_client is not None:
            event_data = await obter_titulo_agenda_evento(assistant, contact)
            if event_data:
                if await agenda_client.confirmar_evento(event_data):
                    await mover_lead(crm_client, contact, company, activity, db)
                    await enviar_mensagem(message, is_audio, media, contact, company, message_client, assistant, db)
                    await encerrar_contato(contact, message_client, db)
                    return True
    except Exception as e:
        logger.exception(f"Error in agenda confirm event pipeline: {e}")
    return False


PIPELINES = {
    "R": _response_pipeline,
    "T": _transfer_pipeline,
    "E": _end_contact_pipeline,
    "M": _migrate_assistant_pipeline,
    "AG": _agenda_check_pipeline,
    "AG-OK": _agenda_create_event_pipeline,
    "AG-RE": _agenda_reschedule_event_pipeline,
    "AG-CN": _agenda_cancel_event_pipeline,
    "AG-CF": _agenda_confirm_event_pipeline
}
