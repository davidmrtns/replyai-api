from sqlalchemy.orm import Session

from app.db.models import Assistant
from app.schemas.assistant_schema import CreateAssistantSchema, UpdateAssistantSchema
from app.utils.model_utils import apply_model_update, get_resource_from_db


async def create_assistant(
    company_id: int, payload: CreateAssistantSchema, db: Session
):
    assistant = Assistant(
        assistant_name=payload.assistant_name,
        instructions=payload.instructions,
        shortcut=payload.shortcut,
        voice_id=payload.voice_id,
        company_id=company_id,
    )

    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant


async def get_assistant(assistant_id: int, company_id: int | None, db: Session):
    return await get_resource_from_db(Assistant, assistant_id, db, company_id)


async def update_assistant(
    assistant_id: int, payload: UpdateAssistantSchema, company_id: int, db: Session
):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)

    apply_model_update(assistant, payload)
    db.commit()
    return assistant


async def delete_assistant(assistant_id: int, company_id: int | None, db: Session):
    assistant = await get_resource_from_db(Assistant, assistant_id, db, company_id)

    if assistant:
        db.delete(assistant)
        db.commit()
        return True
