from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.db.database import obter_sessao
from app.db.models import Midia
from app.db.new_models import Company
from app.routers.media.media_helpers import get_media_from_db
from app.routers.routers_helpers import check_company_access
from app.schemas.atualizacao_empresa_schema import InformacoesMidia, parse_form_data_midia
from app.schemas.empresa_schema import MidiaSchema as MidiaSchemaEmpresa
from app.clients.microsoft.azure_blob_storage_client import AzureBlobStorageClient


router = APIRouter()


@router.post("/{company_slug}")
async def create_media(
        company_slug: str,
        media_file: UploadFile = File(...),
        request: InformacoesMidia = Depends(parse_form_data_midia),
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    filename = f"{media_file.filename}"
    azure_blob_storage_client = AzureBlobStorageClient()

    file_url, upload_filename = azure_blob_storage_client.upload_file(media_file.file, filename)
    if file_url:
        mimetype = media_file.content_type
        media = Midia(
            url=file_url,
            mediatype=mimetype,
            nome=upload_filename,
            atalho=request.atalho,
            ordem=request.ordem,
            id_empresa=company.id
        )

        db.add(media)
        db.commit()
        db.refresh(media)
        return media
    return None


@router.put("/{company_slug}/{media_id}", response_model=MidiaSchemaEmpresa)
async def edit_media(
        company_slug: str,
        media_id: int,
        request: InformacoesMidia,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    media = get_media_from_db(company.id, media_id, db)

    media.atalho = request.atalho
    media.ordem = request.ordem

    db.commit()
    db.refresh(media)
    return media


@router.delete("/{company_slug}/{media_id}")
async def delete_media(
        company_slug: str,
        media_id: int,
        company: Company = Depends(check_company_access),
        db: Session = Depends(obter_sessao)
):
    azure_blob_storage_client = AzureBlobStorageClient()
    media = get_media_from_db(company.id, media_id, db)

    if media and azure_blob_storage_client.delete_file(media.nome):
        db.delete(media)
        db.commit()
        return True
    return False
