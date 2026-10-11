from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.schemas.ai_provider_schema import (
    AIProviderSchema,
    CreateAIProviderSchema,
    UpdateAIProviderSchema,
)
from app.services.ai_provider_service import (
    create_ai_provider as create_ai_provider_service,
    delete_ai_provider as delete_ai_provider_service,
    get_ai_provider as get_ai_provider_service,
    update_ai_provider as update_ai_provider_service,
)
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)

router = APIRouter()


@router.post("/", response_model=AIProviderSchema)
def create_ai_provider(
    request: CreateAIProviderSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return create_ai_provider_service(company_id, request, db)


@router.get("/{ai_provider_id}", response_model=AIProviderSchema)
def get_ai_provider(
    ai_provider_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return get_ai_provider_service(ai_provider_id, company_id, db)


@router.patch("/{ai_provider_id}", response_model=AIProviderSchema)
def update_ai_provider(
    ai_provider_id: int,
    request: UpdateAIProviderSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return update_ai_provider_service(ai_provider_id, request, company_id, db)


@router.delete("/{ai_provider_id}")
def delete_ai_provider(
    ai_provider_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return delete_ai_provider_service(ai_provider_id, company_id, db)
