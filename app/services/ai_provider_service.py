from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.models import AIProvider
from app.schemas.ai_provider_schema import (
    CreateAIProviderSchema,
    UpdateAIProviderSchema,
)
from app.utils.api_key_encryption import encrypt_api_key
from app.utils.model_utils import apply_model_update, get_resource_from_db


def create_ai_provider(company_id: int, payload: CreateAIProviderSchema, db: Session):
    existing_provider = db.query(AIProvider).filter_by(company_id=company_id).first()
    if existing_provider:
        raise HTTPException(
            status_code=409,
            detail="This company already has an AI provider registered",
        )

    ai_provider = AIProvider(
        provider_name=payload.provider_name,
        api_key=encrypt_api_key(payload.api_key),
        company_id=company_id,
    )

    db.add(ai_provider)
    db.commit()
    db.refresh(ai_provider)
    return ai_provider


def get_ai_provider(ai_provider_id: int, company_id: int | None, db: Session):
    return get_resource_from_db(AIProvider, ai_provider_id, db, company_id)


def update_ai_provider(
    ai_provider_id: int,
    payload: UpdateAIProviderSchema,
    company_id: int | None,
    db: Session,
):
    ai_provider = get_resource_from_db(AIProvider, ai_provider_id, db, company_id)
    update_data = payload.model_dump(exclude_unset=True)

    if "api_key" in update_data:
        update_data["api_key"] = encrypt_api_key(update_data["api_key"])

    apply_model_update(ai_provider, update_data)
    db.commit()
    db.refresh(ai_provider)
    return ai_provider


def delete_ai_provider(ai_provider_id: int, company_id: int | None, db: Session):
    ai_provider = get_resource_from_db(AIProvider, ai_provider_id, db, company_id)
    db.delete(ai_provider)
    db.commit()
    return True
