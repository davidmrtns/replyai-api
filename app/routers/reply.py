from datetime import datetime, timezone
from typing import Union

from fastapi import APIRouter
from sqlalchemy.exc import IntegrityError

from app.db.database import get_db_session_with_context
from app.db.models import Company, InboundMessage, MessageClientTypeEnum
from app.exceptions.exceptions import MalformedRequestException
from app.queue.celery_app import celery_app
from app.queue.queue import (
    DEBOUNCE_DELAY_SECONDS,
    get_conversation_key,
    touch_conversation_debounce,
)
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
        integration = MessageClientTypeEnum.evolution
        external_contact_id = request.data.key.remoteJid
        external_message_id = request.data.key.id
    elif isinstance(request, DigisacRequest):
        integration = MessageClientTypeEnum.digisac
        external_contact_id = request.data.contactId
        external_message_id = request.data.id
    else:
        raise MalformedRequestException(
            detail="Unsupported request type.",
            user_friendly_detail="The request is not in the expected format.",
            http_status_code=400,
        )

    # TODO: move the database operations to a service layer for better separation of concerns
    with get_db_session_with_context() as db:
        company = (
            db.query(Company)
            .filter_by(slug=company_slug, token=token, is_active=True)
            .first()
        )
        if not company:
            raise MalformedRequestException(
                detail="Company not found or inactive.",
                user_friendly_detail="The company credentials are invalid.",
                http_status_code=401,
            )

        conversation_key = get_conversation_key(
            company_id=company.id,
            integration=integration.value,
            external_contact_id=external_contact_id,
        )
        inbound_message = InboundMessage(
            company_id=company.id,
            conversation_key=conversation_key,
            integration=integration,
            external_contact_id=external_contact_id,
            external_message_id=external_message_id,
            payload=request.model_dump(mode="json"),
            received_at=datetime.now(timezone.utc),
        )
        db.add(inbound_message)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return {"status": "duplicate"}

    generation = touch_conversation_debounce(conversation_key)
    celery_app.send_task(
        "app.queue.tasks.process_debounce_task",
        args=[conversation_key, generation],
        countdown=DEBOUNCE_DELAY_SECONDS,
    )

    return {"status": "queued"}
