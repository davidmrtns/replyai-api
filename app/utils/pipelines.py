from typing import Tuple
from sqlalchemy.orm import Session
from app.clients.message_client import MessageClient
from app.db.models import Company, Contact
from app.services.company_service import get_assistant_from_company
from app.services.contact_service import update_current_assistant
from app.services.message_service import process_and_send_message
from app.services.thread_service import execute_thread
from app.clients.assistants_client import AssistantReply, AssistantsClient
from app.utils.logger import logger


async def _response_pipeline(
    response: AssistantReply,
    is_audio: bool,
    contact: Contact,
    company_data: Tuple[Company, MessageClient | None],
    assistant: AssistantsClient,
    db: Session,
) -> bool:
    try:
        message, media_code = response.message, response.media_code
        company, message_client = company_data

        await process_and_send_message(
            message,
            is_audio,
            media_code,
            contact,
            company,
            message_client,
            assistant,
            db,
        )  # TODO: add handling for HTTP errors
        return True
    except Exception as e:
        logger.exception(f"Error in response pipeline: {e}")
    return False


async def _migrate_assistant_pipeline(
    response: AssistantReply,
    is_audio: bool,
    contact: Contact,
    company_data: Tuple[Company, MessageClient | None],
    assistant: AssistantsClient,
    db: Session,
) -> bool:
    try:
        message, media_code, assistant_code = (
            response.message,
            response.media_code,
            response.assistant_code,
        )
        company, message_client = company_data

        await process_and_send_message(
            message,
            is_audio,
            media_code,
            contact,
            company,
            message_client,
            assistant,
            db,
        )
        assistant, assistant_id = await get_assistant_from_company(
            company, None, assistant_code, db
        )
        if assistant:
            new_response = await execute_thread(None, None, contact, assistant, db)
            await update_current_assistant(contact, assistant_id, db)
            await process_and_send_message(
                new_response.message,
                is_audio,
                media_code,
                contact,
                company,
                message_client,
                assistant,
                db,
            )
            return True
    except Exception as e:
        logger.exception(f"Error in migrate assistant pipeline: {e}")
    return False


PIPELINES = {"R": _response_pipeline, "M": _migrate_assistant_pipeline}
