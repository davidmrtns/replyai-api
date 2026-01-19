from typing import Union
from fastapi import APIRouter

from app.queue.queue import add_message_to_queue
from app.exceptions.exceptions import MalformedRequestException
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest


router = APIRouter()


@router.post("/{company_slug}/{token}")
async def reply(
    request: Union[EvolutionAPIRequest, DigisacRequest],
    company_slug: str,
    token: str,
):
    if isinstance(request, EvolutionAPIRequest):
        user_id = request.data.key.remoteJid
        payload_type = "evolution"
    elif isinstance(request, DigisacRequest):
        user_id = request.data.contactId
        payload_type = "digisac"
    else:
        raise MalformedRequestException(
            detail="Unsupported request type.",
            user_friendly_detail="The request is not in the expected format.",
            http_status_code=400,
        )

    add_message_to_queue(
        user_id=user_id,
        company_slug=company_slug,
        token=token,
        message_request=request.model_dump(),
        payload_type=payload_type,
    )
    return {"status": "queued"}
