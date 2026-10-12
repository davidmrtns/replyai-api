from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import InboundMessage

MAX_MESSAGE_ATTEMPTS = 5
RETRY_BASE_DELAY_SECONDS = 10
RETRY_MAX_DELAY_SECONDS = 300
PROCESSING_LEASE_SECONDS = 360
CLAIMABLE_STATUSES = ("received", "retrying")


def recover_stale_messages(
    db: Session,
    conversation_key: str,
) -> int:
    """Return messages abandoned by a worker to the retryable state."""
    stale_before = datetime.now(timezone.utc) - timedelta(
        seconds=PROCESSING_LEASE_SECONDS
    )

    recovered_count = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.conversation_key == conversation_key,
            InboundMessage.status == "processing",
            InboundMessage.processing_started_at < stale_before,
        )
        .update(
            {
                InboundMessage.status: "retrying",
                InboundMessage.claim_token: None,
                InboundMessage.next_attempt_at: datetime.now(timezone.utc),
                InboundMessage.last_error: "Processing lease expired",
            },
            synchronize_session=False,
        )
    )

    db.commit()
    return recovered_count


def claim_pending_messages(
    db: Session,
    conversation_key: str,
    limit: int = 50,
) -> tuple[str | None, int, list[dict]]:
    now = datetime.now(timezone.utc)

    messages = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.conversation_key == conversation_key,
            InboundMessage.status.in_(CLAIMABLE_STATUSES),
            or_(
                InboundMessage.next_attempt_at.is_(None),
                InboundMessage.next_attempt_at <= now,
            ),
        )
        .order_by(InboundMessage.received_at.asc(), InboundMessage.id.asc())
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )

    if not messages:
        return None, None, []

    claim_token = str(uuid4())
    company_id = messages[0].company_id

    for message in messages:
        message.status = "processing"
        message.claim_token = claim_token
        message.processing_started_at = now
        message.attempt_count += 1

    db.commit()

    return (
        claim_token,
        company_id,
        [
            {
                "id": message.id,
                "payload": message.payload,
                "integration": message.integration,
            }
            for message in messages
        ],
    )


def mark_messages_completed(
    db: Session,
    message_ids: list[int],
    claim_token: str,
) -> int:
    if not message_ids:
        return 0

    completed_at = datetime.now(timezone.utc)

    updated_count = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.id.in_(message_ids),
            InboundMessage.status == "processing",
            InboundMessage.claim_token == claim_token,
        )
        .update(
            {
                InboundMessage.status: "completed",
                InboundMessage.completed_at: completed_at,
                InboundMessage.claim_token: None,
                InboundMessage.last_error: None,
            },
            synchronize_session=False,
        )
    )

    db.commit()

    return updated_count


def mark_messages_for_retry(
    db: Session,
    message_ids: list[int],
    claim_token: str,
    error: Exception | str,
) -> int:
    if not message_ids:
        return 0

    now = datetime.now(timezone.utc)
    error_message = str(error)[:2000]

    messages = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.id.in_(message_ids),
            InboundMessage.status == "processing",
            InboundMessage.claim_token == claim_token,
        )
        .with_for_update()
        .all()
    )

    for message in messages:
        if message.attempt_count >= MAX_MESSAGE_ATTEMPTS:
            message.status = "dead_letter"
            message.next_attempt_at = None
        else:
            delay = min(
                RETRY_BASE_DELAY_SECONDS * (2 ** max(message.attempt_count - 1, 0)),
                RETRY_MAX_DELAY_SECONDS,
            )

            message.status = "retrying"
            message.next_attempt_at = now + timedelta(seconds=delay)

        message.last_error = error_message
        message.claim_token = None

    db.commit()

    return len(messages)


def mark_messages_dead_letter(
    db: Session,
    message_ids: list[int],
    claim_token: str,
    error: Exception | str,
) -> int:
    if not message_ids:
        return 0

    updated_count = (
        db.query(InboundMessage)
        .filter(
            InboundMessage.id.in_(message_ids),
            InboundMessage.status == "processing",
            InboundMessage.claim_token == claim_token,
        )
        .update(
            {
                InboundMessage.status: "dead_letter",
                InboundMessage.claim_token: None,
                InboundMessage.next_attempt_at: None,
                InboundMessage.last_error: str(error)[:2000],
            },
            synchronize_session=False,
        )
    )

    db.commit()
    return updated_count
