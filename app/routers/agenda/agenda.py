from fastapi import APIRouter
from fastapi.params import Depends
import pytz
from sqlalchemy.orm import Session

from app.db.database import get_db_session
from app.db.models import Agenda
from ..routers_helpers import (
    get_company_id_from_logged_in_user,
    get_company_id_from_user_or_request,
)
from app.schemas.agenda_schema import (
    AgendaSchema,
    CreateAgendaSchema,
    UpdateAgendaSchema,
)
from app.utils.model_utils import get_resource_from_db, apply_model_update


router = APIRouter()


@router.post("/", response_model=AgendaSchema)
async def create_agenda(
    request: CreateAgendaSchema,
    company_id: int = Depends(get_company_id_from_user_or_request),
    db: Session = Depends(get_db_session),
):
    agenda = Agenda(
        endereco=request.address,
        atalho=request.shortcut,
        id_empresa=company_id,
    )

    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda


@router.patch("/{agenda_id}", response_model=AgendaSchema)
async def update_agenda(
    agenda_id: int,
    request: UpdateAgendaSchema,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    agenda = await get_resource_from_db(Agenda, agenda_id, db, company_id)

    apply_model_update(agenda, request)
    db.commit()
    db.refresh(agenda)
    return agenda


@router.delete("/{agenda_id}")
async def delete_agenda(
    agenda_id: int,
    company_id: int | None = Depends(get_company_id_from_logged_in_user),
    db: Session = Depends(get_db_session),
):
    agenda = await get_resource_from_db(Agenda, agenda_id, db, company_id)

    if agenda:
        db.delete(agenda)
        db.commit()
        return True
    return False


@router.get("/timezones")
async def list_timezones():
    return {"timezones": pytz.all_timezones}
