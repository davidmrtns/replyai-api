import pytz
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Agenda
from app.db.new_models import Company
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.atualizacao_empresa_schema import InformacoesAgendaUnica
from app.schemas.empresa_schema import AgendaSchema as AgendaSchemaEmpresa


router = APIRouter()

@router.post("/{slug}")
async def criar_agenda(
        slug: str,
        request: InformacoesAgendaUnica,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    agenda = Agenda(
        endereco=request.endereco,
        atalho=request.atalho,
        id_empresa=empresa.id
    )
    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda

@router.put("/{slug}/{id}", response_model=AgendaSchemaEmpresa)
async def editar_agenda(
        slug: str,
        id: int,
        request: InformacoesAgendaUnica,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    agenda = db.query(Agenda).filter_by(id=id, id_empresa=empresa.id).first()
    if agenda:
        agenda.endereco = request.endereco
        agenda.atalho = request.atalho

        db.commit()
        db.refresh(agenda)
        return agenda
    return None

@router.delete("/{slug}/{id}")
async def excluir_agenda(
        slug: str,
        id: int,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    agenda = db.query(Agenda).filter_by(id=id, id_empresa=empresa.id).first()
    if agenda:
        db.delete(agenda)
        db.commit()
        return True
    return False

@router.get("/fusos")
async def listar_fusos_horarios():
    return {"timezones": pytz.all_timezones}
