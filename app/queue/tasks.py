import asyncio
from typing import List, Union

from app.db.database import get_db_session_with_context
from app.queue.queue import get_and_clear_messages
from app.services.reply_service import ReplyService
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.schemas.integrations.digisac_schema import DigisacRequest


def process_reply(slug: str, token: str, user_id: str, payload_type: str):
    pending_messages = get_and_clear_messages(user_id, slug, token, payload_type)
    if not pending_messages or len(pending_messages) < 1:
        return

    requests: List[Union[EvolutionAPIRequest, DigisacRequest]] = []

    for msg in pending_messages:
        if payload_type == "digisac":
            request = DigisacRequest(**msg)
        elif payload_type == "evolution":
            request = EvolutionAPIRequest(**msg)
        requests.append(request)

    async def _run():
        with get_db_session_with_context() as db:
            reply_service = ReplyService(db, requests)
            await reply_service.generate_reply(slug, token)

    asyncio.run(_run())
