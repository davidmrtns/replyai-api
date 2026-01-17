from fastapi import APIRouter

from app.queue.queue import message_queue
from app.queue.tasks import process_reply
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest


router = APIRouter()


@router.post("/{slug}/{token}")
async def reply(
    request: EvolutionAPIRequest,  # TODO: change to DigisacRequest | EvolutionAPIRequest
    slug: str,
    token: str,
):
    message_queue.enqueue(process_reply, slug, token, request.model_dump())
    return {"status": "queued"}
