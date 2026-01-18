from fastapi import APIRouter

from app.queue.queue import add_message_to_queue
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest


router = APIRouter()


@router.post("/{company_slug}/{token}")
async def reply(
    request: EvolutionAPIRequest,  # TODO: change to DigisacRequest | EvolutionAPIRequest
    company_slug: str,
    token: str,
):
    add_message_to_queue(
        user_id=request.data.key.remoteJid,
        company_slug=company_slug,
        token=token,
        message_request=request.model_dump(),
    )
    return {"status": "queued"}
