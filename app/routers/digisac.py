from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Departamento
from app.db.new_models import Company
from app.db.new_models import DigisacClient
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.integrations_schemas import DigisacClientSchema, DigisacDepartmentSchema
from app.schemas.empresa_schema import DigisacClientSchema as DigisacClientSchemaEmpresa, DepartamentoSchema as DigisacDepartmentSchemaEmpresa
from app.utils.digisac import Digisac


router = APIRouter()

@router.get("/{slug}/servicos")
async def listar_servicos(
        slug: str,
        pagina: int = 1,
        nome: str = None,
        id: str = None,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client_db = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if digisac_client_db:
        digisac_client = Digisac(
            slug=digisac_client_db.digisacSlug,
            service_id=digisac_client_db.service_id,
            defaultUserId=digisac_client_db.digisacDefaultUser,
            defaultAssistantName="",
            token=digisac_client_db.digisacToken
        )
        resposta = digisac_client.listar_servicos(pagina, nome, id)
        return resposta

@router.get("/{slug}/usuarios")
async def listar_usuarios(
        slug: str,
        pagina: int = 1,
        nome: str = None,
        id: str = None,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client_db = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if digisac_client_db:
        digisac_client = Digisac(
            slug=digisac_client_db.digisacSlug,
            service_id=digisac_client_db.service_id,
            defaultUserId=digisac_client_db.digisacDefaultUser,
            defaultAssistantName="",
            token=digisac_client_db.digisacToken
        )
        resposta = digisac_client.listar_usuarios(pagina, nome, id)
        return resposta

@router.get("/{slug}/departamentos")
async def listar_departamentos(
        slug: str,
        pagina: int = 1,
        nome: str = None,
        id: str = None,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client_db = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if digisac_client_db:
        digisac_client = Digisac(
            slug=digisac_client_db.digisacSlug,
            service_id=digisac_client_db.service_id,
            defaultUserId=digisac_client_db.digisacDefaultUser,
            defaultAssistantName="",
            token=digisac_client_db.digisacToken
        )
        resposta = digisac_client.listar_departamentos(pagina, nome, id)
        return resposta

@router.post("/{slug}/departamentos")
async def adicionar_departamento(
        slug: str,
        request: DigisacDepartmentSchema,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if not digisac_client:
        raise HTTPException(status_code=404, detail="Cliente do Digisac não encontrado para essa empresa")

    departamento = Departamento(
        atalho=request.atalho,
        comentario=request.comentario,
        departmentId=request.department_id,
        userId=request.user_id,
        departamento_confirmacao=request.departamento_confirmacao,
        id_digisac_client=digisac_client.id
    )

    db.add(departamento)
    db.commit()
    db.refresh(departamento)
    return departamento

@router.put("/{slug}/departamentos/{id}", response_model=DigisacDepartmentSchemaEmpresa)
async def editar_departamento(
        slug: str,
        id: int,
        request: DigisacDepartmentSchema,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if not digisac_client:
        raise HTTPException(status_code=404, detail="Cliente do Digisac não encontrado para essa empresa")

    departamento = db.query(Departamento).filter_by(id=id, id_digisac_client=digisac_client.id).first()
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento não encontrado para essa cliente do Digisac")

    departamento.atalho = request.atalho
    departamento.comentario = request.comentario
    departamento.departmentId = request.department_id
    departamento.userId = request.user_id
    departamento.departamento_confirmacao = request.departamento_confirmacao
    db.commit()
    return departamento

@router.delete("/{slug}/departamentos/{id}")
async def excluir_departamento(
        slug: str,
        id: int,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if not digisac_client:
        raise HTTPException(status_code=404, detail="Cliente do Digisac não encontrado para essa empresa")

    departamento = db.query(Departamento).filter_by(id=id, id_digisac_client=digisac_client.id).first()
    if departamento:
        db.delete(departamento)
        db.commit()
        return True
    return False

@router.post("/{slug}")
async def criar_digisac_client(
        slug: str,
        request: DigisacClientSchema,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if digisac_client:
        raise HTTPException(status_code=404, detail="Essa empresa já possui um cliente do Digisac")

    digisac_client = DigisacClient(
        digisacSlug=request.slug,
        service_id="",
        digisacToken=request.token,
        digisacDefaultUser="",
        id_empresa=empresa.id
    )

    db.add(digisac_client)
    db.commit()
    db.refresh(digisac_client)
    return digisac_client

@router.put("/{slug}", response_model=DigisacClientSchemaEmpresa)
async def editar_digisac_client(
        slug: str,
        request: DigisacClientSchema,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    digisac_client = db.query(DigisacClient).filter_by(id_empresa=empresa.id).first()
    if not digisac_client:
        raise HTTPException(status_code=404, detail="Cliente do Digisac não encontrado para essa empresa")

    digisac_client.digisacSlug = request.slug
    digisac_client.digisacToken = request.token
    digisac_client.digisacDefaultUser = request.user_id
    digisac_client.service_id = request.service_id
    db.commit()
    return digisac_client
