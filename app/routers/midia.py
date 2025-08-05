from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Midia
from app.db.new_models import Company
from app.routers.empresa import verificar_permissao_empresa
from app.schemas.atualizacao_empresa_schema import InformacoesMidia, parse_form_data_midia
from app.schemas.empresa_schema import MidiaSchema as MidiaSchemaEmpresa
from app.utils.azure_blob_service import AzureBlobService


router = APIRouter()

@router.post("/{slug}")
async def criar_midia(
        slug: str,
        arquivo: UploadFile = File(...),
        request: InformacoesMidia = Depends(parse_form_data_midia),
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    filename = f"{arquivo.filename}"
    client = AzureBlobService()

    url, nome = client.subir_arquivo(arquivo.file, filename)
    if url:
        mimetype = arquivo.content_type
        midia = Midia(
            url=url,
            mediatype=mimetype,
            nome=nome,
            atalho=request.atalho,
            ordem=request.ordem,
            id_empresa=empresa.id
        )

        db.add(midia)
        db.commit()
        db.refresh(midia)
        return midia
    return None

@router.put("/{slug}/{id}", response_model=MidiaSchemaEmpresa)
async def editar_midia(
        slug: str,
        id: int,
        request: InformacoesMidia,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    midia = db.query(Midia).filter_by(id=id, id_empresa=empresa.id).first()
    if midia:
        midia.atalho = request.atalho
        midia.ordem = request.ordem
        db.commit()
        return midia
    return None

@router.delete("/{slug}/{id}")
async def excluir_midia(
        slug: str,
        id: int,
        empresa: Company = Depends(verificar_permissao_empresa),
        db: Session = Depends(obter_sessao)
):
    midia = db.query(Midia).filter_by(id=id, id_empresa=empresa.id).first()
    if midia:
        client = AzureBlobService()
        resposta = client.excluir_arquivo(midia.nome)
        if resposta:
            db.delete(midia)
            db.commit()
            return True
    return False
