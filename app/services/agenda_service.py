import pytz
from sqlalchemy.orm import Session

from app.db.models import Agenda
from app.schemas.agenda_schema import CreateAgendaSchema, UpdateAgendaSchema
from app.utils.model_utils import apply_model_update, get_resource_from_db


def create_agenda(payload: CreateAgendaSchema, company_id: int, db: Session):
    agenda = Agenda(
        address=payload.address,
        shortcut=payload.shortcut,
        company_id=company_id,
    )

    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda


def update_agenda(
    agenda_id: int, request: UpdateAgendaSchema, company_id: int | None, db: Session
):
    agenda = get_resource_from_db(Agenda, agenda_id, db, company_id)

    apply_model_update(agenda, request)
    db.commit()
    db.refresh(agenda)
    return agenda


def delete_agenda(agenda_id: int, company_id: int | None, db: Session):
    agenda = get_resource_from_db(Agenda, agenda_id, db, company_id)

    if agenda:
        db.delete(agenda)
        db.commit()
        return True
    return False


def list_timezones():
    return {"timezones": pytz.all_timezones}
