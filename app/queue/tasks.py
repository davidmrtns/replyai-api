def process_reply(slug: str, token: str, request_data: dict):
    import asyncio
    from app.db.database import get_db_session_with_context
    from app.services.reply_service import ReplyService
    from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest

    request = EvolutionAPIRequest(**request_data)

    async def _run():
        with get_db_session_with_context() as db:
            reply_service = ReplyService(db, request)
            await reply_service.generate_reply(slug, token)

    asyncio.run(_run())
