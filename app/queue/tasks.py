import asyncio
import time
from typing import List, Union

from redis.exceptions import ConnectionError as RedisConnectionError
from requests.exceptions import RequestException
from sqlalchemy.exc import OperationalError

from app.db.database import get_db_session_with_context
from app.queue.celery_app import celery_app
from app.queue.claim_messages import (
    claim_pending_messages,
    mark_messages_dead_letter,
    mark_messages_completed,
    mark_messages_for_retry,
    recover_stale_messages,
)
from app.queue.claim_messages import claim_pending_messages
from app.queue.locks import acquire_conversation_lock, release_conversation_lock
from app.queue.queue import (
    get_conversation_debounce_state,
    get_and_clear_messages,
)
from app.queue.serialization import InvalidInboundMessage, deserialize_messages
from app.services.reply_service import ReplyService
from app.schemas.integrations.evolutionapi_schema import EvolutionAPIRequest
from app.schemas.integrations.digisac_schema import DigisacRequest
from app.utils.logger import logger


@celery_app.task
def process_debounce_task(conversation_key: str, generation: int) -> None:
    current_generation, due_at = get_conversation_debounce_state(conversation_key)

    if current_generation != generation or due_at is None:
        logger.warning(
            "Skipping debounce for %s: expected generation=%s, current generation=%s",
            conversation_key,
            generation,
            current_generation,
        )
        return

    remaining_seconds = due_at - time.time()
    if remaining_seconds > 0:
        logger.info(
            "Debounce still active for %s; rescheduling in %.2f seconds",
            conversation_key,
            remaining_seconds,
        )
        process_debounce_task.apply_async(
            args=[conversation_key, generation],
            countdown=remaining_seconds,
        )
        return

    logger.info(
        "Debounce expired for %s; dispatching conversation task", conversation_key
    )
    process_reply_task.delay(conversation_key)


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
            pass
            # reply_service = ReplyService(db, requests)
            # await reply_service.generate_reply(slug, token)

    asyncio.run(_run())


@celery_app.task(
    bind=True,
    autoretry_for=(
        TimeoutError,
        ConnectionError,
        RedisConnectionError,
        RequestException,
        OperationalError,
    ),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
    soft_time_limit=240,
    time_limit=300,
)
def process_reply_task(self, conversation_key: str):
    lock = acquire_conversation_lock(conversation_key)

    if not lock:
        logger.info(
            "Conversation task skipped because it is already being processed: %s",
            conversation_key,
        )
        return

    claim_token = None
    company_id = None
    messages = []

    try:
        current_generation, due_at = get_conversation_debounce_state(conversation_key)
        if current_generation is None or due_at is None:
            logger.info("No active debounce state for %s", conversation_key)
            return

        remaining_seconds = due_at - time.time()
        if remaining_seconds > 0:
            logger.info(
                "Conversation lock acquired before debounce expired for %s; "
                "rescheduling in %.2f seconds",
                conversation_key,
                remaining_seconds,
            )
            process_debounce_task.apply_async(
                args=[conversation_key, current_generation],
                countdown=remaining_seconds,
            )
            return

        with get_db_session_with_context() as db:
            recover_stale_messages(db, conversation_key)
            claim_token, company_id, messages = claim_pending_messages(
                db, conversation_key
            )

        if not messages:
            return

        try:
            payloads = deserialize_messages(messages)
        except InvalidInboundMessage as error:
            with get_db_session_with_context() as db:
                mark_messages_dead_letter(
                    db=db,
                    message_ids=[message["id"] for message in messages],
                    claim_token=claim_token,
                    error=f"task={self.request.id}: {error}",
                )
            logger.error(
                "Inbound messages moved to dead letter for task %s: %s",
                self.request.id,
                error,
            )
            return

        with get_db_session_with_context() as db:
            reply_service = ReplyService(db)
            asyncio.run(reply_service.generate_reply(company_id, payloads))

        with get_db_session_with_context() as db:
            mark_messages_completed(
                db,
                message_ids=[message["id"] for message in messages],
                claim_token=claim_token,
            )

    except Exception as error:
        with get_db_session_with_context() as db:
            mark_messages_for_retry(
                db=db,
                message_ids=[message["id"] for message in messages],
                claim_token=claim_token,
                error=f"task={self.request.id}: {error}",
            )
        raise
    finally:
        release_conversation_lock(lock)
