from fastapi import APIRouter
from fastapi.params import Depends
import pytz
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.new_models import Company, Agenda
from app.routers.agenda.agenda_helpers import get_agenda
from app.routers.routers_helpers import check_company_access
from app.schemas.atualizacao_empresa_schema import InformacoesAgendaUnica
from app.schemas.empresa_schema import AgendaSchema as AgendaSchemaEmpresa


router = APIRouter()


@router.post("/{company_slug}")
async def create_agenda(
        company_slug: str,
        request: InformacoesAgendaUnica,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    agenda = Agenda(
        endereco=request.endereco,
        atalho=request.atalho,
        id_empresa=company.id
    )

    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda


@router.put("/{company_slug}/{agenda_id}", response_model=AgendaSchemaEmpresa)
async def edit_agenda(
        company_slug: str,
        agenda_id: int,
        request: InformacoesAgendaUnica,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    agenda = get_agenda(company.id, agenda_id, db)

    agenda.endereco = request.endereco
    agenda.atalho = request.atalho

    db.commit()
    db.refresh(agenda)
    return agenda


@router.delete("/{company_slug}/{agenda_id}")
async def delete_agenda(
        company_slug: str,
        agenda_id: int,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    agenda = get_agenda(company.id, agenda_id, db)

    db.delete(agenda)
    db.commit()
    return True


@router.get("/timezones")
async def list_timezones():
    return {"timezones": pytz.all_timezones}
