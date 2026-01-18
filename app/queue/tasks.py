def process_reply(slug: str, token: str, user_id: str):
    import asyncio
    from typing import List
    from app.db.database import get_db_session_with_context
    from app.queue.queue import get_and_clear_messages
    from app.services.reply_service import ReplyService
    from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest

    pending_messages = get_and_clear_messages(user_id, slug, token)
    if not pending_messages or len(pending_messages) < 1:
        return

    requests: List[EvolutionAPIRequest] = []

    for msg in pending_messages:
        request = EvolutionAPIRequest(**msg)
        requests.append(request)

    async def _run():
        with get_db_session_with_context() as db:
            reply_service = ReplyService(db, requests)
            await reply_service.generate_reply(slug, token)

    asyncio.run(_run())
