from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from .routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.agenda_schema import (
    AgendaSchema,
    CreateAgendaSchema,
    UpdateAgendaSchema,
)
from app.services.agenda_service import (
    create_agenda as create_agenda_service,
    update_agenda as update_agenda_service,
    delete_agenda as delete_agenda_service,
    list_timezones as list_timezones_service,
)


router = APIRouter()


@router.post("/", response_model=AgendaSchema)
async def create_agenda(
    request: CreateAgendaSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    return await create_agenda_service(request, company_id, db)


@router.patch("/{agenda_id}", response_model=AgendaSchema)
async def update_agenda(
    agenda_id: int,
    request: UpdateAgendaSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await update_agenda_service(agenda_id, request, company_id, db)


@router.delete("/{agenda_id}")
async def delete_agenda(
    agenda_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    return await delete_agenda_service(agenda_id, company_id, db)


@router.get("/timezones")
async def list_timezones():
    return await list_timezones_service()
