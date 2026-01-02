from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.assistant_schema import (
    AssistantSchema,
    CreateAssistantSchema,
    UpdateAssistantSchema,
)
from app.services.assistant_service import (
    create_assistant as create_assistant_service,
    get_instructions_from_assistant as get_instructions_from_assistant_service,
    update_assistant as update_assistant_service,
    delete_assistant as delete_assistant_service,
)


router = APIRouter()


@router.post("/", response_model=AssistantSchema)
async def create_assistant(
    request: CreateAssistantSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_assistant_service(company_id, request, db)


@router.get("/{assistant_id}")
async def get_instructions_from_assistant(
    assistant_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await get_instructions_from_assistant_service(assistant_id, company_id, db)


@router.patch("/{assistant_id}", response_model=AssistantSchema)
async def update_assistant(
    assistant_id: int,
    request: UpdateAssistantSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_assistant_service(assistant_id, request, company_id, db)


@router.delete("/{assistant_id}")
async def delete_assistente(
    assistant_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_assistant_service(assistant_id, company_id, db)
