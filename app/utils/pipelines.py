from sqlalchemy.orm import Session
from app.db.new_models import Contact
from app.services.company_service import get_assistant_from_company, get_department
from app.services.contact_service import change_awaiting_human_contact, end_contact, transfer_contact, update_current_assistant
from app.services.message_service import process_and_send_message
from app.services.thread_service import execute_thread
from app.types.types import CompanyData
from app.utils.assistants_client import Resposta, AssistantsClient
from app.utils.digisac import Digisac
from app.utils.logger import logger


async def _response_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AssistantsClient,
        db: Session
) -> bool:
    try:
        message, media_code = response.mensagem, response.midia
        company, message_client, _, __ = company_data

        await process_and_send_message(message, is_audio, media_code, contact, company, message_client, assistant, db) # TODO: add handling for HTTP errors
        return True
    except Exception as e:
        logger.exception(f"Error in response pipeline: {e}")
    return False


async def _transfer_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AssistantsClient,
        db: Session
) -> bool:
    try:
        message, media_code, department_code = response.mensagem, response.midia, response.departamento
        company, message_client, _, __ = company_data
        
        if isinstance(message_client, Digisac):
            department = await get_department(company, department_code, False, db)
            if department:
                await process_and_send_message(message, is_audio, media_code, contact, company, message_client, assistant, db)
                await change_awaiting_human_contact(contact, True, db)
                await transfer_contact(message_client, contact, department)
            return True
    except Exception as e:
        logger.exception(f"Error in transfer pipeline: {e}")
    return False


async def _end_contact_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AssistantsClient,
        db: Session
) -> bool:
    try:
        message, media_code = response.mensagem, response.midia
        company, message_client, _, __ = company_data

        await process_and_send_message(message, is_audio, media_code, contact, company, message_client, assistant, db)
        await end_contact(contact, message_client, db)
        return True
    except Exception as e:
        logger.exception(f"Error in end contact pipeline: {e}")
    return False


async def _migrate_assistant_pipeline(
        response: Resposta,
        is_audio: bool,
        contact: Contact,
        company_data: CompanyData,
        assistant: AssistantsClient,
        db: Session
) -> bool:
    try:
        message, media_code, assistant_code = response.mensagem, response.midia, response.assistente
        company, message_client, _, __ = company_data

        await process_and_send_message(message, is_audio, media_code, contact, company, message_client, assistant, db)
        assistant, assistant_id = await get_assistant_from_company(company, None, assistant_code, db)
        if assistant:
            new_response = await execute_thread(None, None, contact, assistant, db)
            await update_current_assistant(contact, assistant_id, db)
            await process_and_send_message(new_response.mensagem, is_audio, media_code, contact, company, message_client, assistant, db)
            return True
    except Exception as e:
        logger.exception(f"Error in migrate assistant pipeline: {e}")
    return False


PIPELINES = {
    "R": _response_pipeline,
    "T": _transfer_pipeline,
    "E": _end_contact_pipeline,
    "M": _migrate_assistant_pipeline
}
