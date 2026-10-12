import json
import os
from redis import Redis
from rq import Queue

REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL, decode_responses=True)
message_queue = Queue("messages", connection=redis_conn)

BASE_KEY_TEMPLATE = "user:{user_id}:company:{company_slug}:{suffix}"
ACTIVE_CHATS_SET_TEMPLATE = "{user_id}:{company_slug}:{token}:{payload_type}"
NEW_CONVERSATION_KEY_TEMPLATE = (
    "conversation:{company_id}:{integration}:{external_contact_id}"
)
DEBOUNCE_KEY_TEMPLATE = "debounce:{conversation_key}"
DEBOUNCE_DELAY_SECONDS = 20
DEBOUNCE_EXPIRY_SECONDS = DEBOUNCE_DELAY_SECONDS


def get_conversation_key(
    company_id: int,
    integration: str,
    external_contact_id: str,
) -> str:
    return NEW_CONVERSATION_KEY_TEMPLATE.format(
        company_id=company_id,
        integration=integration,
        external_contact_id=external_contact_id,
    )


def touch_conversation_debounce(conversation_key: str) -> int:
    debounce_key = DEBOUNCE_KEY_TEMPLATE.format(conversation_key=conversation_key)
    return redis_conn.incr(debounce_key)


def _get_pending_messages_key(user_id: str, company_slug: str) -> str:
    return BASE_KEY_TEMPLATE.format(
        user_id=user_id, company_slug=company_slug, suffix="pending_messages"
    )


def _get_debounce_key(user_id: str, company_slug: str) -> str:
    return BASE_KEY_TEMPLATE.format(
        user_id=user_id, company_slug=company_slug, suffix="debounce"
    )


def _get_active_chats_set(
    user_id: str,
    company_slug: str,
    token: str,
    payload_type: str,
) -> str:
    return ACTIVE_CHATS_SET_TEMPLATE.format(
        user_id=user_id,
        company_slug=company_slug,
        token=token,
        payload_type=payload_type,
    )


def add_message_to_queue(
    user_id: str,
    company_slug: str,
    token: str,
    message_request: dict,
    payload_type: str,
):
    pending_messages_key = _get_pending_messages_key(user_id, company_slug)
    debounce_key = _get_debounce_key(user_id, company_slug)
    active_chats_set = _get_active_chats_set(user_id, company_slug, token, payload_type)

    redis_conn.rpush(pending_messages_key, json.dumps(message_request))
    redis_conn.set(debounce_key, 1, ex=DEBOUNCE_EXPIRY_SECONDS)
    redis_conn.sadd("active_chats", active_chats_set)


def get_and_clear_messages(
    user_id: str,
    company_slug: str,
    token: str,
    message_client_type: str,
):
    pending_messages_key = _get_pending_messages_key(user_id, company_slug)
    active_chats_set = _get_active_chats_set(
        user_id, company_slug, token, message_client_type
    )

    messages = redis_conn.lrange(pending_messages_key, 0, -1)

    redis_conn.delete(pending_messages_key)
    redis_conn.srem("active_chats", active_chats_set)

    return [json.loads(message) for message in messages]


def get_active_chats():
    active_chats = redis_conn.smembers("active_chats")
    return active_chats


def check_debounce(user_id: str, company_slug: str):
    debounce_key = _get_debounce_key(user_id, company_slug)
    return redis_conn.exists(debounce_key)
