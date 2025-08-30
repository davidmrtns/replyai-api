from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.exceptions.exceptions import AIResponseException
from app.schemas.digisac_schema import DigisacRequest
from app.schemas.evolutionapi_schema import EvolutionAPIRequest
from app.services.company_service import get_company_data
from app.services.thread_service import execute_thread
from app.utils.pipelines import PIPELINES
from .reply_helpers import _handle_evolutionapi_request, _handle_digisac_request, _handle_contact_can_receive_replies
from ...services.contact_service import get_or_create_contact
from ...services.message_service import get_message, process_and_send_message


router = APIRouter()


@router.post("/{slug}/{token}")
async def reply(
        request: EvolutionAPIRequest, # TODO: change to DigisacRequest | EvolutionAPIRequest
        slug: str,
        token: str,
        db: Session = Depends(obter_sessao)
):
    reply_result = False

    company_data = await get_company_data(slug, token, db)
    if company_data is None:
        return reply_result

    company, message_client = company_data

    contact, assistant = await get_or_create_contact(request, company_data, db)
    if contact is None:
        return reply_result

    try:
        if not await _handle_contact_can_receive_replies(contact):
            return reply_result

        message, is_audio, image = await get_message(request, message_client, assistant)
        if not message and not image : return reply_result

        if isinstance(request, EvolutionAPIRequest):
            if not await _handle_evolutionapi_request(request, company, message_client, is_audio, db):
                return reply_result
        else:
            if not await _handle_digisac_request(request, contact, db):
                return reply_result

        response = await execute_thread(message, image, contact, assistant, db)
        
        pipeline = PIPELINES.get(response.activity)
        if pipeline:
            reply_result = await pipeline(response, is_audio, contact, company_data, assistant, db)
    except AIResponseException as exc:
        await process_and_send_message(company.ai_reply_error_message, False, None, contact, company, message_client, assistant, db)
        raise exc
    return reply_result
